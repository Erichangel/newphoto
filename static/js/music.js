var MusicPlayer = (function() {
  var audio = null;
  var allMusicList = [];
  var currentMusicName = '';
  var isPlaying = false;
  var autoSwitch = true;
  var autoPlay = true;
  var currentChapter = '';
  var inited = false;
  var errorCount = 0;
  var errorTimer = null;
  var playLock = false;

  var callbacks = {
    stateUpdate: null,
    listUpdate: null,
    listRendered: null,
    settingsUpdate: null,
    showPlayer: null,
    hidePlayer: null,
    chapterMusicData: null,
    ready: null
  };

  function init() {
    audio = document.createElement('audio');
    audio.preload = 'auto';

    var savedState = restoreState();
    if (savedState) {
      audio.src = savedState.src;
      audio.volume = savedState.volume || 0.5;
      currentMusicName = savedState.name;
      if (savedState.playing) {
        audio.addEventListener('canplay', function onCanplay() {
          audio.removeEventListener('canplay', onCanplay);
          audio.currentTime = savedState.time || 0;
          audio.play().then(function() {
            isPlaying = true;
            fireStateUpdate();
          }).catch(function() {});
        });
      }
    } else {
      audio.volume = 0.5;
    }

    audio.addEventListener('ended', function() {
      errorCount = 0;
      playNextMusic();
    });

    audio.addEventListener('error', function() {
      var code = audio.error ? audio.error.code : 0;
      isPlaying = false;
      errorCount++;
      fireStateUpdate();
      if (errorCount > 5) {
        audio.removeAttribute('src');
        audio.load();
        currentMusicName = '';
        return;
      }
      if (currentMusicName && code === 4) {
        allMusicList = allMusicList.filter(function(m) { return m.name !== currentMusicName; });
        currentMusicName = '';
      }
      clearTimeout(errorTimer);
      errorTimer = setTimeout(function() {
        if (allMusicList.length > 0) playNextMusic();
      }, 500);
    });

    window.addEventListener('beforeunload', saveState);
    document.addEventListener('visibilitychange', function() {
      if (document.visibilityState === 'hidden') saveState();
    });

    inited = true;
    if (callbacks.ready) callbacks.ready();
  }

  function saveState() {
    try {
      localStorage.setItem('bgm_state', JSON.stringify({
        name: currentMusicName,
        src: audio.src,
        time: audio.currentTime,
        playing: !audio.paused && !!audio.src,
        volume: audio.volume,
        ts: Date.now()
      }));
    } catch(e) {}
  }

  function restoreState() {
    try {
      var raw = localStorage.getItem('bgm_state');
      if (!raw) return null;
      var s = JSON.parse(raw);
      if (!s || !s.name || !s.src || Date.now() - s.ts > 3600000) {
        localStorage.removeItem('bgm_state');
        return null;
      }
      return s;
    } catch(e) { return null; }
  }

  function fireStateUpdate() {
    if (callbacks.stateUpdate) callbacks.stateUpdate({
      playing: isPlaying,
      name: currentMusicName,
      volume: Math.round(audio.volume * 100)
    });
  }

  function loadMusicList() {
    return fetch('/api/music/list').then(function(r) { return r.json(); }).then(function(data) {
      if (data.ok) {
        allMusicList = data.musics || [];
        if (callbacks.listUpdate) callbacks.listUpdate(allMusicList);
      }
      return data;
    }).catch(function(e) { console.error('[BGM] 加载列表失败:', e); return { ok: false }; });
  }

  function renderMusicList() {
    if (!callbacks.listRendered) return;
    var html = allMusicList.map(function(m) {
      return '<div style="padding:6px 10px;cursor:pointer;border-radius:6px;font-size:12px;color:#333;' +
        (m.name === currentMusicName ? 'background:rgba(233,30,99,0.1);' : '') + '" ' +
        'data-music-name="' + m.name.replace(/"/g, '&quot;') + '">' +
        '<span style="flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + m.name + '</span>' +
        '<span style="font-size:11px;color:#999;margin-left:8px;">' + (m.size_display || '') + '</span>' +
        (m.name === currentMusicName ? ' <i class="fa fa-volume-up" style="color:#E91E63;font-size:11px;"></i>' : '') +
        '</div>';
    }).join('');
    callbacks.listRendered(html);
  }

  function handleVolumeChange(val) {
    audio.volume = val / 100;
    try { localStorage.setItem('musicVolume', val); } catch(e) {}
  }

  function changeVolume(val) {
    handleVolumeChange(val);
  }

  function playSpecificMusic(name, shouldPlay) {
    if (!name) return;
    if (shouldPlay === undefined) shouldPlay = true;
    if (currentMusicName === name && shouldPlay) {
      if (audio.paused) {
        audio.play().catch(function(){});
        isPlaying = true;
        fireStateUpdate();
      }
      return;
    }
    if (playLock) { audio.pause(); }
    playLock = true;
    currentMusicName = name;
    audio.src = '/api/music/serve?f=' + encodeURIComponent(name);
    var savedVolume = localStorage.getItem('musicVolume');
    audio.volume = savedVolume ? savedVolume / 100 : 0.5;
    renderMusicList();
    if (!shouldPlay) {
      playLock = false;
      isPlaying = false;
      fireStateUpdate();
      return;
    }
    var p = audio.play();
    if (p !== undefined) {
      p.then(function() {
        playLock = false;
        isPlaying = true;
        errorCount = 0;
        fireStateUpdate();
      }).catch(function(e) {
        playLock = false;
        if (e.name === 'AbortError') return;
        if (e.name === 'NotAllowedError') {
          isPlaying = false;
          fireStateUpdate();
          return;
        }
        isPlaying = false;
        fireStateUpdate();
      });
    } else {
      playLock = false;
    }
  }

  function playRandomMusic(shouldPlay) {
    if (!allMusicList.length) return;
    var idx = Math.floor(Math.random() * allMusicList.length);
    playSpecificMusic(allMusicList[idx].name, shouldPlay);
  }
  function playPrevMusic() { playRandomMusic(true); }
  function playNextMusic() { playRandomMusic(true); }

  function togglePlayPause() {
    if (audio.error) {
      audio.removeAttribute('src');
      audio.load();
      currentMusicName = '';
      isPlaying = false;
      errorCount = 0;
      playLock = false;
      fireStateUpdate();
      if (allMusicList.length > 0) { playNextMusic(); return; }
      return;
    }
    if (!audio.src && allMusicList.length > 0) { errorCount = 0; playRandomMusic(true); return; }
    if (isPlaying || playLock) {
      audio.pause();
      isPlaying = false;
      playLock = false;
    } else {
      errorCount = 0;
      isPlaying = true;
      audio.play().catch(function(e) {
        isPlaying = false;
        playLock = false;
        if (e.name === 'AbortError') return;
        if (e.name === 'NotAllowedError') return;
      });
    }
    fireStateUpdate();
  }

  function loadSettings() {
    return fetch('/api/music/settings').then(function(r) { return r.json(); }).then(function(data) {
      if (data.ok) {
        autoSwitch = data.settings.auto_switch !== false;
        autoPlay = data.settings.auto_play !== false;
        if (callbacks.settingsUpdate) callbacks.settingsUpdate({ autoPlay: autoPlay, autoSwitch: autoSwitch });
      }
      return data;
    }).catch(function() { return { ok: false }; });
  }

  function getChapterMusic(chapter) {
    return fetch('/api/chapter/music?chapter=' + encodeURIComponent(chapter)).then(function(r) { return r.json(); }).catch(function() { return { ok: false }; });
  }

  function initForChapter(chapter) {
    currentChapter = chapter || '';
    var savedVolume = localStorage.getItem('musicVolume');
    if (savedVolume) {
      audio.volume = savedVolume / 100;
    }

    loadMusicList().then(function() {
      renderMusicList();
      return loadSettings();
    }).then(function() {
      if (allMusicList.length === 0) { return; }

      return getChapterMusic(currentChapter).then(function(chapterRes) {
        var hasChapterMusic = chapterRes.ok && chapterRes.music;
        if (callbacks.chapterMusicData) callbacks.chapterMusicData(hasChapterMusic ? chapterRes.music : '');

        if (hasChapterMusic) {
          if (currentMusicName !== chapterRes.music) { playSpecificMusic(chapterRes.music, autoPlay); }
          return;
        }

        if (!autoSwitch) {
          if (!audio.src) {
            if (autoPlay) playRandomMusic(true);
          }
          return;
        }

        if (!audio.src) playRandomMusic(autoPlay);
      });
    }).catch(function(e) {
      if (!audio.src && allMusicList.length > 0) playRandomMusic(autoPlay);
    });

    if (callbacks.showPlayer) callbacks.showPlayer();
  }

  return {
    init: init,
    initForChapter: initForChapter,
    playSpecificMusic: playSpecificMusic,
    playRandomMusic: playRandomMusic,
    playPrevMusic: playPrevMusic,
    playNextMusic: playNextMusic,
    togglePlayPause: togglePlayPause,
    changeVolume: changeVolume,
    renderMusicList: renderMusicList,
    on: function(event, fn) { callbacks[event] = fn; },
    get audio() { return audio; },
    get isPlaying() { return isPlaying; },
    get currentMusicName() { return currentMusicName; },
    get autoSwitch() { return autoSwitch; },
    get autoPlay() { return autoPlay; }
  };
})();
