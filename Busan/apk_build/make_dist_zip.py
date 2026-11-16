import os
import zipfile
import shutil

root = r"D:\AI_Project_2026_2\Busan"
old = os.path.join(root, "dist", "Busan_Tour_App.zip")
new = os.path.join(root, "dist", "Busan_Tour_App_new.zip")
assets = os.path.join(root, "android", "assets")

# 读取 Android 入口页，并把脚本路径改为 mobile/assets/ 相对路径
index = open(os.path.join(assets, "index.html"), encoding="utf-8").read()
for name in ("data.js", "cloud_snapshot.js", "photos.js", "cloud.js", "app.js", "live.js", "session.js", "planner.js"):
    index = index.replace('src="%s"' % name, 'src="assets/%s"' % name)

with zipfile.ZipFile(old, "r") as zin, zipfile.ZipFile(new, "w", zipfile.ZIP_DEFLATED) as zout:
    replaced = {
        "Busan_Tour_App/Busan旅行助手.apk",
        "Busan_Tour_App/mobile/index.html",
        "Busan_Tour_App/mobile/cloud/spots.json",
    }
    for item in zin.infolist():
        if item.filename in replaced:
            continue
        if item.filename.startswith("Busan_Tour_App/mobile/assets/"):
            continue
        zout.writestr(item, zin.read(item.filename))

    zout.write(os.path.join(root, "dist", "Busan旅行助手.apk"), "Busan_Tour_App/Busan旅行助手.apk")
    zout.writestr("Busan_Tour_App/mobile/index.html", index)
    zout.write(os.path.join(root, "mobile", "cloud", "spots.json"), "Busan_Tour_App/mobile/cloud/spots.json")
    for name in ("data.js", "data.json", "cloud_snapshot.js", "cloud_snapshot.json", "cloud.js", "app.js", "live.js", "session.js", "planner.js", "photos.js", "photos_manifest.json"):
        p = os.path.join(assets, name)
        if os.path.exists(p):
            zout.write(p, "Busan_Tour_App/mobile/assets/" + name)
    photo_dir = os.path.join(assets, "photos")
    if os.path.isdir(photo_dir):
        for name in sorted(os.listdir(photo_dir)):
            p = os.path.join(photo_dir, name)
            if os.path.isfile(p):
                zout.write(p, "Busan_Tour_App/mobile/assets/photos/" + name)

os.replace(new, old)
print("zip rebuilt", os.path.getsize(old))
