// AyushTube Client Application
document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const urlForm = document.getElementById("urlForm");
  const urlInput = document.getElementById("urlInput");
  const pasteBtn = document.getElementById("pasteBtn");
  const clearBtn = document.getElementById("clearBtn");
  const fetchBtn = document.getElementById("fetchBtn");
  const loadingState = document.getElementById("loadingState");
  const loadingTitle = document.getElementById("loadingTitle");
  const loadingSubtitle = document.getElementById("loadingSubtitle");
  const errorState = document.getElementById("errorState");
  const errorTitle = document.getElementById("errorTitle");
  const errorMessage = document.getElementById("errorMessage");
  const dismissErrorBtn = document.getElementById("dismissErrorBtn");
  
  // Single Video Elements
  const resultSection = document.getElementById("resultSection");
  const videoThumb = document.getElementById("videoThumb");
  const videoDuration = document.getElementById("videoDuration");
  const videoTitle = document.getElementById("videoTitle");
  const videoAuthor = document.getElementById("videoAuthor");
  const videoViews = document.getElementById("videoViews");
  const videoDesc = document.getElementById("videoDesc");
  const externalYtLink = document.getElementById("externalYtLink");
  const videoOptionsGrid = document.getElementById("videoOptionsGrid");
  const audioOptionsGrid = document.getElementById("audioOptionsGrid");

  // Playlist Elements
  const playlistSection = document.getElementById("playlistSection");
  const playlistThumb = document.getElementById("playlistThumb");
  const playlistTitle = document.getElementById("playlistTitle");
  const playlistUploader = document.getElementById("playlistUploader");
  const playlistItemCount = document.getElementById("playlistItemCount");
  const playlistFormatSelect = document.getElementById("playlistFormatSelect");
  const downloadPlaylistBtn = document.getElementById("downloadPlaylistBtn");
  const batchDownloadBtnText = document.getElementById("batchDownloadBtnText");
  const selectAllCheckbox = document.getElementById("selectAllCheckbox");
  const selectedCount = document.getElementById("selectedCount");
  const playlistItemsList = document.getElementById("playlistItemsList");

  // Modal Elements
  const downloadModal = document.getElementById("downloadModal");
  const modalTitle = document.getElementById("modalTitle");
  const modalQualityTag = document.getElementById("modalQualityTag");
  const stageBadge = document.getElementById("stageBadge");
  const progressPercent = document.getElementById("progressPercent");
  const progressBar = document.getElementById("progressBar");
  const metricDownloaded = document.getElementById("metricDownloaded");
  const metricDownloadedLabel = document.getElementById("metricDownloadedLabel");
  const metricSpeed = document.getElementById("metricSpeed");
  const metricEta = document.getElementById("metricEta");
  const modalStatusMsg = document.getElementById("modalStatusMsg");
  const directSaveBtn = document.getElementById("directSaveBtn");
  const closeModalBtn = document.getElementById("closeModalBtn");

  // History Elements
  const historyToggleBtn = document.getElementById("historyToggleBtn");
  const historyDrawer = document.getElementById("historyDrawer");
  const closeHistoryBtn = document.getElementById("closeHistoryBtn");
  const clearHistoryBtn = document.getElementById("clearHistoryBtn");
  const historyList = document.getElementById("historyList");
  const historyBadge = document.getElementById("historyBadge");

  // State
  let currentMediaData = null;
  let activeEventSource = null;
  const STORAGE_KEY = "ayushtube_download_history";

  updateHistoryBadge();

  // Input Handlers
  urlInput.addEventListener("input", () => {
    if (urlInput.value.trim().length > 0) {
      clearBtn.classList.remove("hidden");
    } else {
      clearBtn.classList.add("hidden");
    }
  });

  clearBtn.addEventListener("click", () => {
    urlInput.value = "";
    clearBtn.classList.add("hidden");
    urlInput.focus();
  });

  pasteBtn.addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        urlInput.value = text.trim();
        clearBtn.classList.remove("hidden");
        showToast("Pasted from clipboard!", "success");
        fetchMediaMetadata(text.trim());
      }
    } catch (err) {
      showToast("Unable to read clipboard. Please paste manually.", "error");
    }
  });

  // Sample Chips
  document.querySelectorAll(".sample-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const sampleUrl = chip.getAttribute("data-url");
      urlInput.value = sampleUrl;
      clearBtn.classList.remove("hidden");
      fetchMediaMetadata(sampleUrl);
    });
  });

  // Tab Switchers
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const tabType = btn.getAttribute("data-tab");
      if (tabType === "video") {
        document.getElementById("tabVideo").classList.add("active");
      } else {
        document.getElementById("tabAudio").classList.add("active");
      }
    });
  });

  // Form Submit
  urlForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const url = urlInput.value.trim();
    if (!url) return;
    fetchMediaMetadata(url);
  });

  dismissErrorBtn.addEventListener("click", () => {
    errorState.classList.add("hidden");
  });

  // Fetch Media (Video or Playlist)
  async function fetchMediaMetadata(url) {
    errorState.classList.add("hidden");
    resultSection.classList.add("hidden");
    playlistSection.classList.add("hidden");
    
    if (url.includes("list=")) {
      loadingTitle.textContent = "Analyzing Playlist Manifest";
      loadingSubtitle.textContent = "Extracting playlist videos, thumbnails, and item indices...";
    } else {
      loadingTitle.textContent = "Analyzing Media Stream";
      loadingSubtitle.textContent = "Extracting available codecs, highest resolution profiles...";
    }
    
    loadingState.classList.remove("hidden");
    fetchBtn.disabled = true;

    try {
      const res = await fetch("/api/info", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url })
      });

      const json = await res.json();
      if (!res.ok || !json.success) {
        throw new Error(json.detail || "Failed to analyze media.");
      }

      currentMediaData = json.data;
      loadingState.classList.add("hidden");

      if (currentMediaData.is_playlist) {
        renderPlaylistDetails(currentMediaData);
        playlistSection.classList.remove("hidden");
        playlistSection.scrollIntoView({ behavior: "smooth", block: "start" });
      } else {
        renderVideoDetails(currentMediaData);
        resultSection.classList.remove("hidden");
        resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    } catch (err) {
      loadingState.classList.add("hidden");
      errorTitle.textContent = "Extraction Error";
      errorMessage.textContent = err.message || "Failed to fetch media details.";
      errorState.classList.remove("hidden");
      showToast(err.message || "Error fetching media", "error");
    } finally {
      fetchBtn.disabled = false;
    }
  }

  // Render Single Video Details
  function renderVideoDetails(data) {
    videoThumb.src = data.thumbnail || "";
    videoDuration.textContent = data.duration_str || "00:00";
    videoTitle.textContent = data.title;
    videoAuthor.textContent = data.uploader;
    videoViews.textContent = data.view_count;
    videoDesc.textContent = data.description || "No description provided.";
    externalYtLink.href = data.webpage_url;

    videoOptionsGrid.innerHTML = "";
    if (data.video_options && data.video_options.length > 0) {
      data.video_options.forEach(opt => {
        const card = document.createElement("div");
        card.className = `option-card ${opt.recommended ? "recommended" : ""}`;

        let tagClass = "res-tag";
        if (opt.height >= 2160) tagClass += " tag-4k";
        else if (opt.height >= 1080) tagClass += " tag-1080p";

        card.innerHTML = `
          ${opt.recommended ? '<span class="recommended-ribbon">Recommended</span>' : ""}
          <div class="option-header">
            <span class="${tagClass}">${opt.resolution}</span>
            <div class="option-info">
              <div class="option-title">${opt.label}</div>
              <div class="option-meta">
                <span>MP4</span> • <span>${opt.fps} FPS</span> • <span>${opt.size_estimate}</span>
              </div>
            </div>
          </div>
          <p class="option-details">Audio & Video merged seamlessly with FFmpeg</p>
          <button class="btn-download-opt" data-qid="${opt.quality_id}" data-type="video" data-label="${opt.resolution} MP4">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            <span>Download ${opt.resolution}</span>
          </button>
        `;
        videoOptionsGrid.appendChild(card);
      });
    }

    audioOptionsGrid.innerHTML = "";
    if (data.audio_options && data.audio_options.length > 0) {
      data.audio_options.forEach(opt => {
        const card = document.createElement("div");
        card.className = `option-card ${opt.recommended ? "recommended" : ""}`;

        card.innerHTML = `
          ${opt.recommended ? '<span class="recommended-ribbon">Best Quality</span>' : ""}
          <div class="option-header">
            <span class="res-tag tag-audio">${opt.format.toUpperCase()}</span>
            <div class="option-info">
              <div class="option-title">${opt.label}</div>
              <div class="option-meta">
                <span>${opt.format.toUpperCase()}</span> • <span>${opt.quality}</span>
              </div>
            </div>
          </div>
          <p class="option-details">${opt.description}</p>
          <button class="btn-download-opt" data-qid="${opt.quality_id}" data-type="audio" data-label="${opt.format.toUpperCase()} (${opt.quality})">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            <span>Extract ${opt.format.toUpperCase()}</span>
          </button>
        `;
        audioOptionsGrid.appendChild(card);
      });
    }

    document.querySelectorAll(".btn-download-opt").forEach(btn => {
      btn.addEventListener("click", () => {
        const qid = btn.getAttribute("data-qid");
        const type = btn.getAttribute("data-type");
        const label = btn.getAttribute("data-label");
        startDownload(qid, type, label);
      });
    });
  }

  // Render Playlist Details
  function renderPlaylistDetails(data) {
    playlistThumb.src = data.thumbnail || "";
    playlistTitle.textContent = data.title;
    playlistUploader.textContent = `By ${data.uploader}`;
    playlistItemCount.textContent = data.total_count;

    playlistItemsList.innerHTML = "";
    data.items.forEach((item, idx) => {
      const row = document.createElement("div");
      row.className = "playlist-item-row";
      row.innerHTML = `
        <div class="playlist-item-check">
          <input type="checkbox" class="playlist-checkbox" data-index="${idx}" checked />
        </div>
        <span class="playlist-item-index">${item.index}</span>
        <img class="playlist-item-thumb" src="${item.thumbnail}" alt="thumb" loading="lazy" />
        <div class="playlist-item-info">
          <div class="playlist-item-title" title="${item.title}">${item.title}</div>
          <div class="playlist-item-duration">${item.duration_str}</div>
        </div>
      `;
      playlistItemsList.appendChild(row);
    });

    updateSelectedCount();

    // Checkbox Listeners
    selectAllCheckbox.checked = true;
    selectAllCheckbox.onchange = () => {
      const checked = selectAllCheckbox.checked;
      document.querySelectorAll(".playlist-checkbox").forEach(cb => cb.checked = checked);
      updateSelectedCount();
    };

    document.querySelectorAll(".playlist-checkbox").forEach(cb => {
      cb.onchange = () => {
        updateSelectedCount();
      };
    });
  }

  function updateSelectedCount() {
    const total = document.querySelectorAll(".playlist-checkbox").length;
    const checked = document.querySelectorAll(".playlist-checkbox:checked").length;
    selectedCount.textContent = checked;
    batchDownloadBtnText.textContent = `Download Selected (${checked} Videos) as ZIP`;
    downloadPlaylistBtn.disabled = checked === 0;
  }

  // Playlist Batch Download Trigger
  downloadPlaylistBtn.addEventListener("click", async () => {
    if (!currentMediaData || !currentMediaData.items) return;

    const checkedBoxes = Array.from(document.querySelectorAll(".playlist-checkbox:checked"));
    if (checkedBoxes.length === 0) {
      showToast("Please select at least 1 video to download.", "error");
      return;
    }

    const selectedItems = checkedBoxes.map(cb => {
      const idx = parseInt(cb.getAttribute("data-index"));
      return currentMediaData.items[idx];
    });

    const formatVal = playlistFormatSelect.value.split("|");
    const qualityId = formatVal[0];
    const formatType = formatVal[1];
    const label = `Playlist ZIP (${selectedItems.length} items)`;

    // Open Modal
    modalTitle.textContent = currentMediaData.title;
    modalQualityTag.textContent = label;
    stageBadge.className = "stage-badge downloading";
    stageBadge.textContent = "Batch Processing";
    progressPercent.textContent = "0%";
    progressBar.style.width = "0%";
    metricDownloadedLabel.textContent = "Items";
    metricDownloaded.textContent = `0 / ${selectedItems.length}`;
    metricSpeed.textContent = "Initializing...";
    metricEta.textContent = "--:--";
    modalStatusMsg.textContent = `Preparing download queue for ${selectedItems.length} videos...`;
    directSaveBtn.classList.add("hidden");
    downloadModal.classList.remove("hidden");

    try {
      const res = await fetch("/api/playlist/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          playlist_title: currentMediaData.title,
          items: selectedItems,
          quality_id: qualityId,
          format_type: formatType
        })
      });

      const json = await res.json();
      if (!res.ok || !json.success) {
        throw new Error(json.detail || "Could not start playlist download.");
      }

      listenToProgress(json.task_id, label, true);
    } catch (err) {
      stageBadge.className = "stage-badge error";
      stageBadge.textContent = "Failed";
      modalStatusMsg.textContent = err.message || "Failed to start playlist download.";
      showToast(err.message || "Download failed", "error");
    }
  });

  // Single Video Download Trigger
  async function startDownload(qualityId, formatType, label) {
    if (!currentMediaData) return;

    if (activeEventSource) {
      activeEventSource.close();
      activeEventSource = null;
    }

    modalTitle.textContent = currentMediaData.title;
    modalQualityTag.textContent = label;
    stageBadge.className = "stage-badge downloading";
    stageBadge.textContent = "Downloading";
    progressPercent.textContent = "0%";
    progressBar.style.width = "0%";
    metricDownloadedLabel.textContent = "Downloaded";
    metricDownloaded.textContent = "0 MB / --";
    metricSpeed.textContent = "Connecting...";
    metricEta.textContent = "--:--";
    modalStatusMsg.textContent = "Establishing connection to streaming server...";
    directSaveBtn.classList.add("hidden");
    downloadModal.classList.remove("hidden");

    try {
      const res = await fetch("/api/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: currentMediaData.webpage_url,
          quality_id: qualityId,
          format_type: formatType,
          title: currentMediaData.title
        })
      });

      const json = await res.json();
      if (!res.ok || !json.success) {
        throw new Error(json.detail || "Could not initialize download.");
      }

      listenToProgress(json.task_id, label, false);
    } catch (err) {
      stageBadge.className = "stage-badge error";
      stageBadge.textContent = "Failed";
      modalStatusMsg.textContent = err.message || "Failed to start download.";
      showToast(err.message || "Download failed", "error");
    }
  }

  // SSE Progress Listener
  function listenToProgress(taskId, label, isPlaylist = false) {
    const sse = new EventSource(`/api/progress/${taskId}`);
    activeEventSource = sse;

    sse.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const percent = Math.min(Math.max(data.percent || 0, 0), 100);
        progressPercent.textContent = `${percent.toFixed(1)}%`;
        progressBar.style.width = `${percent}%`;

        if (isPlaylist || data.is_playlist) {
          metricDownloadedLabel.textContent = "Queue";
          metricDownloaded.textContent = `${data.current_item || 0} / ${data.total_items || "--"}`;
          if (data.current_title) {
            modalStatusMsg.textContent = `Downloading [${data.current_item}/${data.total_items}]: ${data.current_title}`;
          }
        } else {
          metricDownloadedLabel.textContent = "Downloaded";
          metricDownloaded.textContent = `${data.downloaded || "0 MB"} / ${data.total || "--"}`;
          if (data.status === "downloading") {
            modalStatusMsg.textContent = "Streaming chunks from YouTube CDN...";
          }
        }

        metricSpeed.textContent = data.speed || "Calculating...";
        metricEta.textContent = data.eta || "--:--";

        if (data.status === "downloading") {
          stageBadge.className = "stage-badge downloading";
          stageBadge.textContent = isPlaylist ? "Batch Downloading" : "Downloading";
        } else if (data.status === "converting") {
          stageBadge.className = "stage-badge converting";
          stageBadge.textContent = "Muxing / Processing";
          modalStatusMsg.textContent = "Multiplexing video and high-fidelity audio streams with FFmpeg...";
        } else if (data.status === "compressing") {
          stageBadge.className = "stage-badge converting";
          stageBadge.textContent = "Packaging ZIP";
          modalStatusMsg.textContent = "Compressing all playlist files into a single ZIP archive...";
        } else if (data.status === "completed" || data.ready_for_download) {
          stageBadge.className = "stage-badge completed";
          stageBadge.textContent = "Ready!";
          progressPercent.textContent = "100%";
          progressBar.style.width = "100%";
          modalStatusMsg.textContent = "Success! File generated and ready to save.";

          const fileUrl = `/api/file/${taskId}`;
          directSaveBtn.href = fileUrl;
          directSaveBtn.classList.remove("hidden");

          // Auto-trigger browser download
          const autoDownloadLink = document.createElement("a");
          autoDownloadLink.href = fileUrl;
          autoDownloadLink.setAttribute("download", data.filename || (isPlaylist ? "playlist.zip" : "video.mp4"));
          document.body.appendChild(autoDownloadLink);
          autoDownloadLink.click();
          document.body.removeChild(autoDownloadLink);

          saveToHistory({
            title: data.title || currentMediaData.title,
            quality: label,
            filename: data.filename,
            date: new Date().toLocaleDateString(),
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            fileUrl: fileUrl
          });

          showToast("Download ready! Saved to your device.", "success");
          sse.close();
        } else if (data.status === "error") {
          stageBadge.className = "stage-badge error";
          stageBadge.textContent = "Error";
          modalStatusMsg.textContent = data.error || "An error occurred during download.";
          showToast(data.error || "Download error", "error");
          sse.close();
        }
      } catch (e) {
        console.error("SSE parse error:", e);
      }
    };

    sse.onerror = () => {
      sse.close();
    };
  }

  // Close Modal
  closeModalBtn.addEventListener("click", () => {
    downloadModal.classList.add("hidden");
    if (activeEventSource) {
      activeEventSource.close();
      activeEventSource = null;
    }
  });

  // History Management
  function getHistory() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  function saveToHistory(item) {
    const list = getHistory();
    list.unshift(item);
    if (list.length > 25) list.pop();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    updateHistoryBadge();
    renderHistoryDrawer();
  }

  function updateHistoryBadge() {
    const list = getHistory();
    historyBadge.textContent = list.length;
  }

  function renderHistoryDrawer() {
    const list = getHistory();
    historyList.innerHTML = "";

    if (list.length === 0) {
      historyList.innerHTML = '<div class="history-empty">No downloads yet. Download your first video or playlist!</div>';
      return;
    }

    list.forEach(item => {
      const el = document.createElement("div");
      el.className = "history-item";
      el.innerHTML = `
        <div class="history-item-title">${item.title}</div>
        <div class="history-item-meta">
          <span class="quality-pill">${item.quality}</span>
          <span>${item.date} ${item.time}</span>
        </div>
      `;
      historyList.appendChild(el);
    });
  }

  historyToggleBtn.addEventListener("click", () => {
    renderHistoryDrawer();
    historyDrawer.classList.remove("hidden");
  });

  closeHistoryBtn.addEventListener("click", () => {
    historyDrawer.classList.add("hidden");
  });

  clearHistoryBtn.addEventListener("click", () => {
    localStorage.removeItem(STORAGE_KEY);
    updateHistoryBadge();
    renderHistoryDrawer();
    showToast("History cleared.", "success");
  });

  // Toast System
  function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let icon = "ℹ️";
    if (type === "success") icon = "✅";
    if (type === "error") icon = "❌";

    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    document.getElementById("toastContainer").appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(50px)";
      toast.style.transition = "all 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, 3800);
  }
});
