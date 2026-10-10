-- Conky widget click + hover handler. This build calls the hook named
-- `on_mouse` (no conky_ prefix), so both names are defined to be safe.
local hover_y = nil
local colours = {}
local regions = {}
local appearance = 0
local cairo_available = pcall(require, "cairo")

local function blend(key, base, target)
    local current = colours[key] or {tonumber(base:sub(1,2),16),
        tonumber(base:sub(3,4),16), tonumber(base:sub(5,6),16)}
    local desired = {tonumber(target:sub(1,2),16),
        tonumber(target:sub(3,4),16), tonumber(target:sub(5,6),16)}
    for i = 1, 3 do current[i] = current[i] + (desired[i] - current[i]) * 0.45 end
    colours[key] = current
    return string.format("%02X%02X%02X", math.floor(current[1]+0.5),
        math.floor(current[2]+0.5), math.floor(current[3]+0.5))
end

local function header_top()
    local map = io.open(conky_bt_layout_map or "/tmp/conky_bt_layout.tsv", "r")
    if map then
        local first = map:read("*l") or ""
        map:close()
        return (tonumber(first:match("^(%d+)")) or 538) - 60
    end
    return 478
end

local function pending_status(mac)
    if not mac or not mac:match("^[%x:]+$") then return nil end
    local home = os.getenv("HOME") or "/home/lonzo"
    local f = io.open(home .. "/.cache/conky_bt_pending_" .. mac:gsub(":", ""), "r")
    if not f then return nil end
    local line = f:read("*l") or ""
    f:close()
    local state, started = line:match("^(%a+)\t(%d+)$")
    if (state == "connecting" or state == "disconnecting") and
        os.time() - tonumber(started) < 60 then return state end
    return nil
end

function conky_bt_status(mac, connected)
    local busy = pending_status(mac)
    local status = busy and (busy .. "…") or (connected == "1" and "connected" or "disconnected")
    local colour = busy and "B3BDC7" or (connected == "1" and "8B969F" or "74808D")
    return "${font DejaVu Sans:size=9}${color " .. colour .. "}• " .. status .. "${font}"
end

local function is_left(b)
    return b == "left" or b == 1 or b == "1"
end

local function handle(event)
    if not event then return false end

    if event.type == "mouse_enter" or event.type == "mouse_move" then
        hover_y = tonumber(event.y)
        return false
    elseif event.type == "mouse_leave" then
        hover_y = nil
        return false
    end

    if event.type == "button_down" and is_left(event.button) then
        local y, x = event.y or 0, event.x or 0
        local dev, mac, action = "", nil, nil
        local map = io.open(conky_bt_layout_map or "/tmp/conky_bt_layout.tsv", "r")
        if map then
            for line in map:lines() do
                local y0, y1, name, address, sx0, sx1, nx1 = line:match(
                    "^(%d+)\t(%d+)\t([^\t]+)\t([%x:]+)\t[01]\t(%d+)\t(%d+)\t(%d+)$")
                if y0 and y1 and y >= tonumber(y0) and y < tonumber(y1) then
                    -- Only the first text line is actionable; battery bars remain passive.
                    if y >= tonumber(y0) + 14 and y < tonumber(y0) + 40 then
                        if x >= tonumber(sx0) and x <= tonumber(sx1) then
                            action = "toggle"
                        elseif x >= 4 and x <= tonumber(nx1) then
                            action = "settings"
                        end
                    end
                    dev, mac = name, address
                    break
                end
            end
            map:close()
        end
        -- Record the selected row so real clicks can distinguish layout errors
        -- from Settings navigation errors.
        local log = io.open("/tmp/conky_bt_click.log", "a")
        if log then
            log:write(os.date("%Y-%m-%d %H:%M:%S"), "\ty=", tostring(y),
                      "\tx=", tostring(x), "\tdevice=", dev,
                      "\taction=", action or "none", "\n")
            log:close()
        end
        if mac then
            if action == "toggle" then
                if pending_status(mac) then return true end
                os.execute("/home/lonzo/.config/conky/toggle_bt_device.sh '" .. mac .. "' >/dev/null 2>&1 &")
            elseif action == "settings" then
                os.execute("/home/lonzo/.config/conky/open_bt_device.sh '" ..
                    dev:gsub("'", "'\\''") .. "' >/dev/null 2>&1 &")
            else
                return false
            end
        else
            local top = header_top()
            if y < top or y >= top + 60 then return false end
            os.execute("/home/lonzo/.config/conky/open_bt_device.sh '' &")
        end
        return true
    end
    return false
end

function conky_on_mouse(event) return handle(event) end
function on_mouse(event) return handle(event) end

-- Hover updates are local to each Conky window, with a short colour fade.
function conky_bt_header()
    local top = header_top()
    local hovering = hover_y and hover_y >= top and hover_y < top + 60
    local colour = blend("header", "CBD5E1", hovering and "ECEFF4" or "CBD5E1")
    return "${color " .. colour .. "}${font DejaVu Sans:bold:size=16}" ..
           "Bluetooth${font}${color}"
end

function conky_bt_row_color(y0, y1, base)
    y0, y1 = tonumber(y0), tonumber(y1)
    if y0 and y1 then regions[y0] = {last = y1, seen = tonumber(conky_parse("${updates}")) or 0} end
    local hovering = hover_y and y0 and y1 and hover_y >= y0 and hover_y < y1
    local target = base
    if hovering then target = base == "D8DEE9" and "ECEFF4" or "B8CDD5" end
    local colour = blend(tostring(y0) .. base, base, target)
    return "${color " .. colour .. "}"
end

local function rounded(cr, x, y, width, height, radius)
    cairo_new_sub_path(cr)
    cairo_arc(cr, x + width - radius, y + radius, radius, -math.pi/2, 0)
    cairo_arc(cr, x + width - radius, y + height - radius, radius, 0, math.pi/2)
    cairo_arc(cr, x + radius, y + height - radius, radius, math.pi/2, math.pi)
    cairo_arc(cr, x + radius, y + radius, radius, math.pi, 3*math.pi/2)
    cairo_close_path(cr)
end

function conky_panel_background()
    if not cairo_available or not conky_window then return end
    local w = conky_window
    if not w.display or not w.drawable or w.width <= 0 or w.height <= 0 then return end
    local surface = cairo_xlib_surface_create(w.display, w.drawable, w.visual, w.width, w.height)
    local cr = cairo_create(surface)
    appearance = appearance + (1 - appearance) * 0.35
    -- Both configs define their own alpha so a shared hook can draw either card.
    local alpha = conky_panel_opacity or 0.32
    rounded(cr, 1, 1, w.width - 2, w.height - 2, 14)
    cairo_set_source_rgba(cr, 0.09, 0.105, 0.125, alpha * appearance)
    cairo_fill_preserve(cr)
    cairo_set_source_rgba(cr, 1, 1, 1, 0.10 * appearance)
    cairo_set_line_width(cr, 1)
    cairo_stroke(cr)
    local updates = tonumber(conky_parse("${updates}")) or 0
    local top = header_top()
    local function highlight(key, y0, y1)
        local state = regions[key .. "_fade"] or 0
        local active = hover_y and hover_y >= y0 and hover_y < y1
        state = state + ((active and 1 or 0) - state) * 0.4
        regions[key .. "_fade"] = state
        if state > 0.005 then
            rounded(cr, 5, y0 + 2, w.width - 10, y1 - y0 - 4, 8)
            cairo_set_source_rgba(cr, 1, 1, 1, 0.075 * state * appearance)
            cairo_fill(cr)
        end
    end
    highlight("header", top, top + 60)
    for y0, region in pairs(regions) do
        if type(y0) == "number" and region.seen >= updates - 1 then
            highlight(tostring(y0), y0, region.last)
        end
    end
    cairo_destroy(cr)
    cairo_surface_destroy(surface)
end

-- Read the CPU package sensor, rediscovering its hwmon number after reboot.
local cpu_temp_path = nil
local cpu_temp_second = -1
local cpu_temp_value = "—"
function conky_cpu_temperature()
    local now = os.time()
    if now == cpu_temp_second then return cpu_temp_value end
    cpu_temp_second = now
    if not cpu_temp_path then
        for i = 0, 31 do
            local path = "/sys/class/hwmon/hwmon" .. i
            local f = io.open(path .. "/name", "r")
            if f then
                local name = f:read("*l")
                f:close()
                if name == "coretemp" then cpu_temp_path = path .. "/temp1_input"; break end
            end
        end
    end
    local f = cpu_temp_path and io.open(cpu_temp_path, "r")
    if f then
        local value = tonumber(f:read("*l"))
        f:close()
        if value then cpu_temp_value = string.format("%.0f°C", value / 1000); return cpu_temp_value end
    end
    cpu_temp_path = nil
    cpu_temp_value = "—"
    return cpu_temp_value
end

local system_os_name = nil
function conky_os_name()
    if not system_os_name then
        system_os_name = "Linux"
        local f = io.open("/etc/os-release", "r")
        if f then
            for line in f:lines() do
                local value = line:match('^PRETTY_NAME="(.*)"$')
                if value then system_os_name = value; break end
            end
            f:close()
        end
    end
    return system_os_name
end
function conky_user_name()
    return os.getenv("USER") or "lonzo"
end
