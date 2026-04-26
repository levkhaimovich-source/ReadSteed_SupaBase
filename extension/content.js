// ReadSteed Content Script

const READSTEED_URL = "https://www.readsteed.com/app?extension=true";
let floatingBtn = null;
let overlayContainer = null;
let iframe = null;
let hideButtonTimeout = null;

function normalizeText(text) {
  if (!text) return "";
  return text
    .replace(/[\r\n]+/g, ' ') // Replace line breaks with spaces
    .replace(/\s+/g, ' ')     // Normalize multiple spaces
    .trim();
}

function getSelectedText() {
  const selection = window.getSelection();
  return selection ? selection.toString() : "";
}

// --- Floating Button Logic ---

function createFloatingButton() {
  if (floatingBtn) return;
  
  floatingBtn = document.createElement("button");
  floatingBtn.id = "readsteed-floating-btn";
  floatingBtn.innerHTML = "Read ⚡";
  
  floatingBtn.addEventListener("mousedown", (e) => {
    // Prevent selection clearing
    e.preventDefault();
  });
  
  floatingBtn.addEventListener("click", () => {
    const text = normalizeText(getSelectedText());
    if (text) {
      openReaderOverlay(text);
    }
    hideFloatingButton();
  });
  
  document.body.appendChild(floatingBtn);
}

function showFloatingButton(x, y) {
  if (!floatingBtn) createFloatingButton();
  
  clearTimeout(hideButtonTimeout);
  
  // Position above and slightly to the right of the cursor
  floatingBtn.style.left = `${x + 10}px`;
  floatingBtn.style.top = `${Math.max(0, y - 40)}px`;
  floatingBtn.classList.add("rs-visible");
}

function hideFloatingButton() {
  if (floatingBtn && floatingBtn.classList.contains("rs-visible")) {
    floatingBtn.classList.remove("rs-visible");
  }
}

// Handle text selection
document.addEventListener("mouseup", (e) => {
  // Ignore clicks on our own UI
  if (e.target.id === "readsteed-floating-btn" || e.target.id === "readsteed-iframe") {
    return;
  }
  
  // Small delay to let browser finish selection
  setTimeout(() => {
    const text = normalizeText(getSelectedText());
    if (text.length > 0) {
      // Show button near cursor
      showFloatingButton(e.pageX, e.pageY);
    } else {
      hideFloatingButton();
    }
  }, 10);
});

// Hide button on mousedown outside
document.addEventListener("mousedown", (e) => {
  if (e.target.id !== "readsteed-floating-btn") {
    hideFloatingButton();
  }
});

// --- Overlay & Iframe Logic ---

function createOverlay() {
  if (overlayContainer) return;
  
  overlayContainer = document.createElement("div");
  overlayContainer.id = "readsteed-overlay-container";
  
  iframe = document.createElement("iframe");
  iframe.id = "readsteed-iframe";
  iframe.src = READSTEED_URL;
  iframe.allowFullscreen = true;
  
  overlayContainer.appendChild(iframe);
  document.body.appendChild(overlayContainer);
  
  // Prevent scrolling on body
  document.body.style.overflow = 'hidden';
}

function closeOverlay() {
  if (overlayContainer) {
    overlayContainer.classList.remove("rs-visible");
    document.body.style.overflow = '';
    
    // Wait for fade out
    setTimeout(() => {
      if (overlayContainer && overlayContainer.parentNode) {
        overlayContainer.parentNode.removeChild(overlayContainer);
      }
      overlayContainer = null;
      iframe = null;
    }, 300);
  }
}

function openReaderOverlay(text) {
  if (!text) return;
  
  createOverlay();
  
  // Trigger fade in
  requestAnimationFrame(() => {
    overlayContainer.classList.add("rs-visible");
  });
  
  // Wait for iframe to load before sending text
  iframe.onload = () => {
    // Send text to the ReadSteed app inside the iframe
    iframe.contentWindow.postMessage({
      type: "RSVP_START_READER",
      text: text
    }, "https://www.readsteed.com");
  };
}

// --- Communication ---

// Listen for messages from Background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "open_reader") {
    const text = normalizeText(request.text);
    if (text) openReaderOverlay(text);
  } else if (request.action === "open_reader_from_shortcut") {
    const text = normalizeText(getSelectedText());
    if (text) {
      openReaderOverlay(text);
    }
  }
});

// Listen for messages from the ReadSteed iframe (e.g. to close the overlay)
window.addEventListener("message", (event) => {
  // Verify origin for security
  if (event.origin !== "https://www.readsteed.com" && event.origin !== "http://localhost:5000" && event.origin !== "http://127.0.0.1:5000") {
    return;
  }
  
  if (event.data && event.data.type === "RSVP_CLOSE_OVERLAY") {
    closeOverlay();
  }
});

// Also close on ESC key if not handled by iframe
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && overlayContainer) {
    closeOverlay();
  }
});
