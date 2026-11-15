/* live.js —— 实时定位与「到景点距离」条
 *
 * 原生壳用 LocationManager 每 3 秒 / 12 米回传一次坐标；网页只负责把坐标
 * 转成到目标景点（或最近景点）的直线距离，绝不推断实时营业或拥挤程度。
 */
(function () {
  var st = { pos: null, target: null, watching: false, error: "", waitTimer: null };
  var watchId = null;

  function lang() { return (window.BusanUI && BusanUI.getLang()) || "zh"; }
  function T(zh, ko, en) { return lang() === "zh" ? zh : lang() === "ko" ? ko : en; }

  function spotById(id) {
    var list = (window.BusanCloud && BusanCloud.allSpots()) || [];
    for (var i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
    return null;
  }

  function bestNear() {
    if (!st.pos || !window.BusanCloud) return null;
    var rows = BusanCloud.nearby(st.pos.lat, st.pos.lng, 2);
    return rows.length ? rows[0] : null;
  }

  function fmt(km) {
    if (km == null || !isFinite(km)) return "";
    return km < 10 ? km.toFixed(1) : String(Math.round(km));
  }

  function paint() {
    var text = document.getElementById("liveText");
    var dot = document.getElementById("liveDot");
    var btn = document.getElementById("liveBtn");
    if (!text || !dot || !btn) return;

    btn.textContent = st.watching ? T("停止", "중지", "Stop") : T("实时", "실시간", "Live");
    btn.classList.toggle("on", st.watching);
    dot.classList.toggle("on", st.watching && !!st.pos);

    if (st.error) {
      text.textContent = st.error;
      return;
    }
    if (!st.watching && !st.pos) {
      text.textContent = T("实时定位未开启 · 开启后显示到景点距离", "실시간 위치 꺼짐 · 켜면 명소까지 거리 표시", "Live location off · turn on to see distance");
      return;
    }
    if (!st.pos) {
      text.textContent = T("正在获取位置…", "위치를 확인하는 중…", "Getting your location…");
      return;
    }
    var acc = st.pos.accuracy ? " · ±" + Math.round(st.pos.accuracy) + " m" : "";
    if (st.target) {
      var s = spotById(st.target);
      if (s && s.lat != null) {
        var km = window.BusanCloud.haversine(st.pos.lat, st.pos.lng, s.lat, s.lng);
        text.textContent = T("距 ", "距 ", "To ") + (window.BusanCloud ? BusanCloud.spotTitle(s) : s.name) +
          " " + fmt(km) + " km · " + T("实时", "실시간", "live") + acc;
        return;
      }
    }
    var near = bestNear();
    if (near) {
      text.textContent = T("最近 ", "가장 가까운 ", "Nearest ") + BusanCloud.spotTitle(near.spot) +
        " " + fmt(near.km) + " km · " + T("实时", "실시간", "live") + acc;
    } else {
      text.textContent = T("已定位 · 附近没有收录景点", "위치 확인됨 · 주변 수록 명소 없음", "Located · no covered spot nearby") + acc;
    }
  }

  function start() {
    if (st.watching) return;
    st.error = "";
    st.watching = true;
    paint();

    if (window.BusanHost && typeof window.BusanHost.startLocationWatch === "function") {
      var ok = false;
      try { ok = window.BusanHost.startLocationWatch(); } catch (e) { ok = false; }
      if (!ok) {
        // 原生已弹出系统授权框；授权后会直接开始回传坐标
        clearTimeout(st.waitTimer);
        st.waitTimer = setTimeout(function () {
          if (!st.pos && st.watching) {
            st.error = T("等待定位授权…", "위치 권한을 기다리는 중…", "Waiting for location permission…");
            paint();
          }
        }, 4000);
      }
      return;
    }

    if (navigator.geolocation) {
      watchId = navigator.geolocation.watchPosition(function (p) {
        update(p.coords.latitude, p.coords.longitude, p.coords.accuracy, "web", Date.now());
      }, function () {
        st.error = T("定位失败，请检查权限", "위치 확인 실패, 권한을 확인하세요", "Location failed — check permission");
        st.watching = false;
        paint();
      }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 5000 });
    } else {
      st.error = T("这台设备不支持定位", "이 기기에서는 위치를 지원하지 않습니다", "Location not supported on this device");
      st.watching = false;
      paint();
    }
  }

  function stop() {
    if (watchId != null && navigator.geolocation) {
      navigator.geolocation.clearWatch(watchId);
      watchId = null;
    }
    if (window.BusanHost && typeof window.BusanHost.stopLocationWatch === "function") {
      try { window.BusanHost.stopLocationWatch(); } catch (e) {}
    }
    st.watching = false;
    st.error = "";
    paint();
  }

  function update(lat, lng, acc, provider, at) {
    st.pos = { lat: lat, lng: lng, accuracy: acc, provider: provider, at: at || Date.now() };
    st.watching = true;
    st.error = "";
    clearTimeout(st.waitTimer);
    paint();
  }

  window.__busanLocUpdate = function (lat, lng, acc, provider, at) {
    update(lat, lng, acc, provider, at);
  };

  window.__busanLocError = function (code, msg) {
    st.error = code === 1
      ? T("定位权限被拒绝，可在系统设置里开启", "위치 권한이 거부됨. 시스템 설정에서 허용하세요", "Location denied — enable it in system settings")
      : T("定位不可用，请检查 GPS 或网络", "위치를 사용할 수 없음. GPS·네트워크를 확인하세요", "Location unavailable — check GPS or network");
    st.watching = false;
    paint();
  };

  window.BusanLive = {
    init: function () {
      var btn = document.getElementById("liveBtn");
      if (btn) btn.onclick = function () { st.watching ? stop() : start(); };
      paint();
    },
    start: start,
    stop: stop,
    paint: paint,
    position: function () { return st.pos; },
    isWatching: function () { return st.watching; },
    setTarget: function (id) {
      st.target = id || null;
      paint();
    },
    target: function () { return st.target; }
  };
})();
