[app]

# App identity
title = Goodwill Fee Manager
package.name = goodwillfee
package.domain = org.goodwill.tuition

# Source
source.dir = .
source.include_exts = py,ttf,json,png

# Version
version = 1.0

# Requirements — keep minimal for a clean first build
requirements = python3,kivy

# Orientation: portrait suits a phone fee list
orientation = portrait

# Fullscreen off (keep the status bar)
fullscreen = 0

# Android API levels (safe modern defaults)
android.api = 33
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a

# Permissions: none needed for v1 (local storage only)
# android.permissions =

# Keep the build simple — no extra services
android.allow_backup = True

[buildozer]

# Verbosity: 2 shows full logs (useful for first builds)
log_level = 2
warn_on_root = 1
