chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "readsteed-read",
    title: "Read with ReadSteed",
    contexts: ["selection"]
  });
});

// Handle context menu click
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "readsteed-read" && info.selectionText) {
    chrome.tabs.sendMessage(tab.id, {
      action: "open_reader",
      text: info.selectionText
    });
  }
});

// Handle keyboard shortcut
chrome.commands.onCommand.addListener((command, tab) => {
  if (command === "read_selection") {
    // Send message to content script to grab selection and open reader
    chrome.tabs.sendMessage(tab.id, { action: "open_reader_from_shortcut" });
  }
});
