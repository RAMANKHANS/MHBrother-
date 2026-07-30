[app]

title = MH Brother
package.name = mhbrother
package.domain = org.mhbrother

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,json,atlas
source.exclude_dirs = .git,.github,.buildozer,bin,__pycache__,venv
source.exclude_exts = pyc,pyo

version = 1.0

requirements = python3,kivy,requests,pyjnius,certifi,urllib3,idna,charset-normalizer

orientation = portrait
fullscreen = 0

android.api = 33
android.minapi = 21
android.ndk = 25c
android.archs = arm64-v8a,armeabi-v7a

android.permissions = INTERNET,READ_MEDIA_IMAGES

android.accept_sdk_license = True

presplash.color = #FFFFFF

log_level = 2
warn_on_root = 1

[buildozer]

log_level = 2