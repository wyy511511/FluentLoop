-- Fluent Lab: Hammerspoon system-wide recording hotkeys.
-- Copy into ~/.hammerspoon/init.lua (or append to your existing file).
-- Use absolute paths and ensure Hammerspoon has Accessibility permission.
local recorder = os.getenv("HOME") .. "/FluentLab/tools/quick-record.sh"
local function togglePractice(purpose)
  local task = hs.task.new("/bin/zsh", function(code, stdout, stderr)
    local message = (stdout or "") .. (stderr or "")
    local saved = message:match("SAVED:([^\r\n]+)")
    if saved then
      hs.pasteboard.setContents(saved)
      hs.alert.show("Fluent Lab: saved · path copied")
    elseif message:find("RECORDING:", 1, true) then
      hs.alert.show("Fluent Lab: recording " .. purpose .. " ●")
    else
      hs.alert.show("Fluent Lab: " .. message:sub(1, 180))
    end
  end, {recorder, purpose})
  if task then task:start() else hs.alert.show("Could not start Fluent Lab recorder") end
end
-- Press the same shortcut again to stop. A different purpose shortcut also stops.
hs.hotkey.bind({"cmd", "alt", "shift"}, "R", function() togglePractice("speaking") end)
hs.hotkey.bind({"cmd", "alt", "shift"}, "G", function() togglePractice("grammar") end)
hs.hotkey.bind({"cmd", "alt", "shift"}, "C", function() togglePractice("compression") end)
hs.hotkey.bind({"cmd", "alt", "shift"}, "I", function() togglePractice("interview") end)
