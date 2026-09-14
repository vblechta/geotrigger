#!/usr/bin/env bash
# Build the GeoTrigger Android APK from the command line (no Android Studio).
#
# Usage (from anywhere):
#   ./android/build.sh              # debug APK you can install on a phone
#   ./android/build.sh --install    # build, then install over USB (adb)
#   ./android/build.sh --release    # release APK (still debug-signed)
#   ./android/build.sh --help
#
# First run downloads a JDK (if needed), Gradle, and libraries — several hundred MB.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/geotrigger"
DIST="$ROOT/dist"
WANT_INSTALL=0
BUILD_TASK="assembleDebug"
APK_REL="app/build/outputs/apk/debug/app-debug.apk"
APK_NAME="GeoTrigger-debug.apk"

usage() {
  cat <<'EOF'
Build the GeoTrigger Android app without Android Studio.

  ./android/build.sh              Build a debug APK
  ./android/build.sh --install    Build and install on a connected phone
  ./android/build.sh --release    Build a release APK
  ./android/build.sh --help       Show this help

The APK is copied to android/dist/. To install it by hand, copy that file to
the phone and open it (enable “Install unknown apps” for the file manager).

For --install, enable USB debugging: Settings → About phone → tap Build
number seven times, then Settings → Developer options → USB debugging.
EOF
}

log() { printf '==> %s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing command '$1'. Install it and re-run."
}

java_major() {
  local home="$1"
  "$home/bin/java" -version 2>&1 | awk -F[\".] '/version/ { print ($2=="1") ? $3 : $2; exit }'
}

find_jdk() {
  local candidate major
  local -a candidates=(
    "${JAVA_HOME:-}"
    "$CACHE/jdk-21"
    "$HOME/android-studio/jbr"
    /opt/android-studio/jbr
    /usr/lib/jvm/java-21-openjdk
    /usr/lib/jvm/java-17-openjdk
    /usr/lib/jvm/jbrsdk
  )

  if command -v java >/dev/null 2>&1; then
    candidates+=("$(dirname "$(dirname "$(readlink -f "$(command -v java)")")")")
  fi

  for candidate in "${candidates[@]}"; do
    [[ -n "$candidate" && -x "$candidate/bin/javac" && -x "$candidate/bin/java" ]] || continue
    major="$(java_major "$candidate")"
    if [[ "$major" -ge 17 && "$major" -le 21 ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

install_jdk() {
  need_cmd curl
  need_cmd tar
  local arch api_arch tarball tmp
  arch="$(uname -m)"
  case "$arch" in
    x86_64) api_arch=x64 ;;
    aarch64|arm64) api_arch=aarch64 ;;
    *) die "Unsupported CPU architecture: $arch" ;;
  esac

  mkdir -p "$CACHE"
  tarball="$CACHE/jdk-21.tar.gz"
  tmp="$CACHE/jdk-21-unpack"
  log "Downloading JDK 21 (Temurin) for $arch — one-time, cached in $CACHE"
  curl -fL --progress-bar \
    "https://api.adoptium.net/v3/binary/latest/21/ga/linux/${api_arch}/jdk/hotspot/normal/eclipse?project=jdk" \
    -o "$tarball"
  rm -rf "$tmp"
  mkdir -p "$tmp"
  tar -xzf "$tarball" -C "$tmp"
  rm -rf "$CACHE/jdk-21"
  mv "$tmp"/jdk-21* "$CACHE/jdk-21"
  rm -rf "$tmp" "$tarball"
  [[ -x "$CACHE/jdk-21/bin/javac" ]] || die "JDK download did not contain javac."
}

ensure_jdk() {
  local home
  if home="$(find_jdk)"; then
    export JAVA_HOME="$home"
    log "Using JDK $JAVA_HOME (Java $(java_major "$JAVA_HOME"))"
    return
  fi
  if [[ -d "$CACHE/jdk-21" && ! -x "$CACHE/jdk-21/bin/javac" ]]; then
    rm -rf "$CACHE/jdk-21"
  fi
  if [[ ! -x "$CACHE/jdk-21/bin/javac" ]]; then
    install_jdk
  fi
  export JAVA_HOME="$CACHE/jdk-21"
  log "Using JDK $JAVA_HOME (Java $(java_major "$JAVA_HOME"))"
}

find_sdk() {
  local candidate
  local -a candidates=(
    "${ANDROID_HOME:-}"
    "${ANDROID_SDK_ROOT:-}"
    "$HOME/Android/Sdk"
    "$HOME/Android/sdk"
    /opt/android-sdk
  )
  if [[ -f "$ROOT/local.properties" ]]; then
    candidate="$(sed -n 's/^sdk.dir=//p' "$ROOT/local.properties" | tail -n1 | sed 's/\\:/:/g')"
    candidates=("$candidate" "${candidates[@]}")
  fi
  for candidate in "${candidates[@]}"; do
    [[ -n "$candidate" && -d "$candidate" ]] || continue
    if [[ -d "$candidate/platforms" || -d "$candidate/cmdline-tools" || -d "$candidate/platform-tools" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

accept_licenses() {
  local sdk="$1"
  mkdir -p "$sdk/licenses"
  printf '24333f8a63b6825ea9c5514f83c2829b004d1fee\n' >"$sdk/licenses/android-sdk-license"
  printf '84831b9409646161da1e9e3e0c60b8c8\n' >"$sdk/licenses/android-sdk-preview-license"
}

install_cmdline_tools() {
  local sdk="$1"
  need_cmd curl
  need_cmd unzip
  local zip="$CACHE/commandlinetools.zip"
  mkdir -p "$CACHE" "$sdk"
  log "Downloading Android command-line tools into $sdk"
  curl -fL --progress-bar \
    "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip" \
    -o "$zip"
  rm -rf "$sdk/cmdline-tools/latest" "$sdk/cmdline-tools/tmp-unpack"
  mkdir -p "$sdk/cmdline-tools/tmp-unpack"
  unzip -q "$zip" -d "$sdk/cmdline-tools/tmp-unpack"
  mkdir -p "$sdk/cmdline-tools"
  # Zip contains a "cmdline-tools" folder; SDK expects cmdline-tools/latest.
  if [[ -d "$sdk/cmdline-tools/tmp-unpack/cmdline-tools" ]]; then
    mv "$sdk/cmdline-tools/tmp-unpack/cmdline-tools" "$sdk/cmdline-tools/latest"
  else
    mv "$sdk/cmdline-tools/tmp-unpack"/* "$sdk/cmdline-tools/latest"
  fi
  rm -rf "$sdk/cmdline-tools/tmp-unpack" "$zip"
}

sdkmanager_bin() {
  local sdk="$1"
  local bin
  for bin in \
    "$sdk/cmdline-tools/latest/bin/sdkmanager" \
    "$sdk/cmdline-tools/bin/sdkmanager"; do
    if [[ -x "$bin" ]]; then
      printf '%s\n' "$bin"
      return 0
    fi
  done
  # Android Studio sometimes puts versioned cmdline-tools here.
  local found
  found="$(find "$sdk/cmdline-tools" -type f -name sdkmanager 2>/dev/null | head -n1 || true)"
  if [[ -n "$found" && -x "$found" ]]; then
    printf '%s\n' "$found"
    return 0
  fi
  return 1
}

ensure_sdk_packages() {
  local sdk="$1"
  local mgr
  local have_platform=0 have_build_tools=0
  [[ -d "$sdk/platforms/android-35" ]] && have_platform=1
  if compgen -G "$sdk/build-tools/35.*" >/dev/null; then
    have_build_tools=1
  fi
  if [[ "$have_platform" -eq 1 && "$have_build_tools" -eq 1 ]]; then
    log "Android SDK ready at $sdk"
    return
  fi

  if ! mgr="$(sdkmanager_bin "$sdk")"; then
    install_cmdline_tools "$sdk"
    mgr="$(sdkmanager_bin "$sdk")" || die "sdkmanager is not available after installing command-line tools."
  fi

  accept_licenses "$sdk"
  log "Installing Android SDK packages (platform 35, build-tools 35, platform-tools)"
  "$mgr" --sdk_root="$sdk" \
    "platforms;android-35" \
    "build-tools;35.0.0" \
    "platform-tools"
  [[ -d "$sdk/platforms/android-35" ]] || die "Failed to install Android SDK platform 35."
}

write_local_properties() {
  local sdk="$1"
  # Gradle wants unescaped paths; backslashes only matter on Windows.
  printf 'sdk.dir=%s\n' "$sdk" >"$ROOT/local.properties"
}

build_apk() {
  need_cmd chmod
  chmod +x "$ROOT/gradlew"
  log "Building $BUILD_TASK (first run downloads Gradle and dependencies)"
  (
    cd "$ROOT"
    ./gradlew --no-daemon "$BUILD_TASK"
  )
  if [[ "$BUILD_TASK" == "assembleRelease" ]]; then
    if [[ -f "$ROOT/app/build/outputs/apk/release/app-release.apk" ]]; then
      APK_REL="app/build/outputs/apk/release/app-release.apk"
      APK_NAME="GeoTrigger-release.apk"
    else
      APK_REL="app/build/outputs/apk/release/app-release-unsigned.apk"
      APK_NAME="GeoTrigger-release-unsigned.apk"
    fi
  fi
  local built="$ROOT/$APK_REL"
  [[ -f "$built" ]] || die "Gradle finished but the APK was not found at $APK_REL"
  mkdir -p "$DIST"
  cp -f "$built" "$DIST/$APK_NAME"
  log "APK: $DIST/$APK_NAME"
}

install_apk() {
  local apk="$DIST/$APK_NAME"
  local adb_bin=""
  if command -v adb >/dev/null 2>&1; then
    adb_bin="$(command -v adb)"
  elif [[ -x "${ANDROID_HOME:-$HOME/Android/Sdk}/platform-tools/adb" ]]; then
    adb_bin="${ANDROID_HOME:-$HOME/Android/Sdk}/platform-tools/adb"
  fi
  [[ -n "$adb_bin" ]] || die "adb not found. Install the APK by copying $apk to the phone instead."
  log "Installing on the device with adb"
  if ! "$adb_bin" devices | awk 'NR>1 && $2=="device" { found=1 } END { exit !found }'; then
    die "No phone/emulator in 'device' state. Plug it in, accept the USB debugging prompt, then retry --install."
  fi
  "$adb_bin" install -r "$apk"
  log "Installed GeoTrigger. Open it on the phone and sign in with the server URL."
}

for arg in "$@"; do
  case "$arg" in
    --help|-h) usage; exit 0 ;;
    --install) WANT_INSTALL=1 ;;
    --release)
      BUILD_TASK="assembleRelease"
      APK_REL="app/build/outputs/apk/release/app-release-unsigned.apk"
      APK_NAME="GeoTrigger-release-unsigned.apk"
      ;;
    *) die "Unknown option: $arg (try --help)" ;;
  esac
done

ensure_jdk
export PATH="$JAVA_HOME/bin:$PATH"

SDK_DIR="$(find_sdk || true)"
if [[ -z "$SDK_DIR" ]]; then
  SDK_DIR="$HOME/Android/Sdk"
  log "No Android SDK found; using $SDK_DIR"
fi
export ANDROID_HOME="$SDK_DIR"
export ANDROID_SDK_ROOT="$SDK_DIR"
accept_licenses "$SDK_DIR"
ensure_sdk_packages "$SDK_DIR"
write_local_properties "$SDK_DIR"

build_apk

printf '\nBuild finished.\n  Install file: %s\n' "$DIST/$APK_NAME"
printf '  Copy that APK to your phone and open it, or run:\n    %s --install\n' "$0"

if [[ "$WANT_INSTALL" -eq 1 ]]; then
  install_apk
fi
