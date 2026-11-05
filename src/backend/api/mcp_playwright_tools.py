"""Official Playwright MCP Tools Specifications (70+ tools).

Includes Core, Network (--caps=network), Storage (--caps=storage),
Testing (--caps=testing), DevTools (--caps=devtools), PDF (--caps=pdf),
Vision (--caps=vision), and Config (--caps=config).
"""
from __future__ import annotations

from typing import Any, Dict, List

PLAYWRIGHT_MCP_TOOLS: List[Dict[str, Any]] = [
    # ==========================================
    # Core (24 tools)
    # ==========================================
    {
        "name": "browser_navigate",
        "description": "Navigate browser page to the specified URL.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to navigate to"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "browser_navigate_back",
        "description": "Navigate back to previous page in browser history.",
        "parameters_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "browser_snapshot",
        "description": "Capture a complete accessibility snapshot or DOM tree snapshot of current page.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "full_tree": {"type": "boolean", "description": "Capture entire DOM tree"}
            }
        }
    },
    {
        "name": "browser_find",
        "description": "Find elements on page matching selector or text query.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Selector or text query to find elements"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "browser_click",
        "description": "Click an element by selector, coordinates, or text.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Selector or text of element to click"}
            },
            "required": ["selector"]
        }
    },
    {
        "name": "browser_hover",
        "description": "Hover mouse cursor over element matching selector.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Selector of element to hover"}
            },
            "required": ["selector"]
        }
    },
    {
        "name": "browser_drag",
        "description": "Initiate drag gesture on element matching source selector.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Selector of element to drag"}
            },
            "required": ["source"]
        }
    },
    {
        "name": "browser_drop",
        "description": "Drop dragged element onto target element matching selector.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Selector of target element to drop onto"}
            },
            "required": ["target"]
        }
    },
    {
        "name": "browser_type",
        "description": "Type text into currently focused or selected element.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to type"},
                "selector": {"type": "string", "description": "Target selector (optional)"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "browser_fill_form",
        "description": "Fill multiple form fields with key-value data.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "fields": {"type": "object", "description": "Map of field selectors to values"}
            },
            "required": ["fields"]
        }
    },
    {
        "name": "browser_select_option",
        "description": "Select option(s) in a dropdown select element.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Select element selector"},
                "value": {"type": "string", "description": "Option value or label to select"}
            },
            "required": ["selector", "value"]
        }
    },
    {
        "name": "browser_press_key",
        "description": "Press a specific keyboard key or key combination.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key or shortcut, e.g. Enter, Tab, Control+A"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "browser_take_screenshot",
        "description": "Capture screenshot image of viewport or specific element.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to save screenshot"},
                "full_page": {"type": "boolean", "description": "Capture full scrollable page"}
            }
        }
    },
    {
        "name": "browser_tabs",
        "description": "List, switch between, open, or close browser tabs.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "new", "switch", "close"], "description": "Tab action"},
                "index": {"type": "integer", "description": "Target tab index"}
            }
        }
    },
    {
        "name": "browser_handle_dialog",
        "description": "Accept or dismiss JavaScript alert, confirm, or prompt dialog.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["accept", "dismiss"], "description": "Dialog response action"},
                "prompt_text": {"type": "string", "description": "Text to enter for prompt dialog"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "browser_file_upload",
        "description": "Upload file(s) into an input element.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "File input selector"},
                "files": {"type": "array", "items": {"type": "string"}, "description": "Paths to files to upload"}
            },
            "required": ["selector", "files"]
        }
    },
    {
        "name": "browser_console_messages",
        "description": "Retrieve console messages, warnings, and errors from current page.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "level": {"type": "string", "enum": ["info", "warning", "error", "all"], "description": "Minimum log level"}
            }
        }
    },
    {
        "name": "browser_network_requests",
        "description": "List network requests captured on current page.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "filter": {"type": "string", "description": "URL substring or resource type to filter by"}
            }
        }
    },
    {
        "name": "browser_network_request",
        "description": "Inspect specific network request and response details.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "request_id": {"type": "string", "description": "ID of request to inspect"}
            },
            "required": ["request_id"]
        }
    },
    {
        "name": "browser_evaluate",
        "description": "Evaluate JavaScript expression in page context.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "JavaScript expression to evaluate"}
            },
            "required": ["expression"]
        }
    },
    {
        "name": "browser_run_code_unsafe",
        "description": "Execute arbitrary Playwright code in sandbox context.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Playwright JS/TS snippet to execute"}
            },
            "required": ["code"]
        }
    },
    {
        "name": "browser_wait_for",
        "description": "Wait for a selector, timeout, or condition to be satisfied.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Element selector to wait for"},
                "timeout_ms": {"type": "integer", "description": "Timeout in milliseconds"}
            }
        }
    },
    {
        "name": "browser_close",
        "description": "Close current page or entire browser session.",
        "parameters_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "browser_resize",
        "description": "Resize viewport dimensions of current page.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "width": {"type": "integer", "description": "Viewport width in pixels"},
                "height": {"type": "integer", "description": "Viewport height in pixels"}
            },
            "required": ["width", "height"]
        }
    },

    # ==========================================
    # Network (--caps=network, 4 tools)
    # ==========================================
    {
        "name": "browser_route",
        "description": "Mock, intercept, or modify network requests matching URL pattern.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "url_pattern": {"type": "string", "description": "Glob or regex URL pattern"},
                "status": {"type": "integer", "description": "Mock HTTP status code"},
                "body": {"type": "string", "description": "Mock response body"}
            },
            "required": ["url_pattern"]
        }
    },
    {
        "name": "browser_route_list",
        "description": "List all active network route interceptors.",
        "parameters_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "browser_unroute",
        "description": "Remove active network route interceptor.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "url_pattern": {"type": "string", "description": "URL pattern of route to remove"}
            },
            "required": ["url_pattern"]
        }
    },
    {
        "name": "browser_network_state_set",
        "description": "Emulate network conditions (offline, throughput, latency).",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "offline": {"type": "boolean", "description": "Emulate offline mode"},
                "latency_ms": {"type": "number", "description": "Latency in milliseconds"}
            }
        }
    },

    # ==========================================
    # Storage (--caps=storage, 17 tools)
    # ==========================================
    {
        "name": "browser_cookie_list",
        "description": "List all cookies for current page URL context.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "urls": {"type": "array", "items": {"type": "string"}, "description": "Optional list of URLs"}
            }
        }
    },
    {
        "name": "browser_cookie_get",
        "description": "Get specific cookie by name.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Cookie name"}
            },
            "required": ["name"]
        }
    },
    {
        "name": "browser_cookie_set",
        "description": "Set cookie with name, value, domain, and security attributes.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Cookie name"},
                "value": {"type": "string", "description": "Cookie value"},
                "domain": {"type": "string", "description": "Cookie domain"},
                "path": {"type": "string", "description": "Cookie path"}
            },
            "required": ["name", "value"]
        }
    },
    {
        "name": "browser_cookie_delete",
        "description": "Delete specific cookie by name and domain.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Cookie name"},
                "domain": {"type": "string", "description": "Cookie domain"}
            },
            "required": ["name"]
        }
    },
    {
        "name": "browser_cookie_clear",
        "description": "Clear all cookies in the browser context.",
        "parameters_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "browser_localstorage_list",
        "description": "List all key-value entries in localStorage.",
        "parameters_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "browser_localstorage_get",
        "description": "Get value of localStorage key.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Storage key name"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "browser_localstorage_set",
        "description": "Set value of localStorage key.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Storage key name"},
                "value": {"type": "string", "description": "Storage string value"}
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "browser_localstorage_delete",
        "description": "Delete key from localStorage.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Storage key name"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "browser_localstorage_clear",
        "description": "Clear all entries in localStorage.",
        "parameters_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "browser_sessionstorage_list",
        "description": "List all key-value entries in sessionStorage.",
        "parameters_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "browser_sessionstorage_get",
        "description": "Get value of sessionStorage key.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Storage key name"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "browser_sessionstorage_set",
        "description": "Set value of sessionStorage key.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Storage key name"},
                "value": {"type": "string", "description": "Storage string value"}
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "browser_sessionstorage_delete",
        "description": "Delete key from sessionStorage.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Storage key name"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "browser_sessionstorage_clear",
        "description": "Clear all entries in sessionStorage.",
        "parameters_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "browser_storage_state",
        "description": "Export complete browser storage state (cookies, localStorage) as JSON.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional file path to save storage state"}
            }
        }
    },
    {
        "name": "browser_set_storage_state",
        "description": "Restore browser storage state from JSON string or file path.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "state": {"type": "object", "description": "Storage state object"},
                "path": {"type": "string", "description": "Path to storage state JSON file"}
            }
        }
    },

    # ==========================================
    # Testing (--caps=testing, 5 tools)
    # ==========================================
    {
        "name": "browser_generate_locator",
        "description": "Generate optimal Playwright locator for an element.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Source element selector or text"}
            },
            "required": ["selector"]
        }
    },
    {
        "name": "browser_verify_element_visible",
        "description": "Assert element is visible in the viewport.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Element selector to verify"},
                "timeout_ms": {"type": "integer", "description": "Timeout in milliseconds"}
            },
            "required": ["selector"]
        }
    },
    {
        "name": "browser_verify_text_visible",
        "description": "Assert text is present and visible on page.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Expected text string"},
                "timeout_ms": {"type": "integer", "description": "Timeout in milliseconds"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "browser_verify_list_visible",
        "description": "Assert list of elements or options is visible.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "List container or item selector"},
                "expected_count": {"type": "integer", "description": "Expected number of visible items"}
            },
            "required": ["selector"]
        }
    },
    {
        "name": "browser_verify_value",
        "description": "Assert element input or attribute value matches expected value.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Element selector"},
                "expected_value": {"type": "string", "description": "Expected value"}
            },
            "required": ["selector", "expected_value"]
        }
    },

    # ==========================================
    # DevTools (--caps=devtools, 13 tools)
    # ==========================================
    {
        "name": "browser_start_tracing",
        "description": "Start Playwright performance and action tracing.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "screenshots": {"type": "boolean", "description": "Include screenshots in trace"},
                "snapshots": {"type": "boolean", "description": "Include DOM snapshots"}
            }
        }
    },
    {
        "name": "browser_stop_tracing",
        "description": "Stop tracing and save trace artifact.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to save trace zip"}
            }
        }
    },
    {
        "name": "browser_start_video",
        "description": "Start recording video of browser session.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "dir": {"type": "string", "description": "Directory to record video to"}
            }
        }
    },
    {
        "name": "browser_stop_video",
        "description": "Stop video recording and finalize media file.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Output path for video file"}
            }
        }
    },
    {
        "name": "browser_video_chapter",
        "description": "Add chapter or bookmark milestone to recording.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Chapter title or milestone description"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "browser_video_show_actions",
        "description": "Highlight user interactions and cursor actions in video.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean", "description": "Enable action visual overlays"}
            }
        }
    },
    {
        "name": "browser_video_hide_actions",
        "description": "Hide user action overlays in video recording.",
        "parameters_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "browser_start_recording",
        "description": "Begin recording DevTools events and actions.",
        "parameters_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "browser_stop_recording",
        "description": "Stop DevTools action recording.",
        "parameters_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "browser_highlight",
        "description": "Highlight DOM element with bounding box overlay.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Selector to highlight"},
                "color": {"type": "string", "description": "Overlay color hex or name"}
            },
            "required": ["selector"]
        }
    },
    {
        "name": "browser_hide_highlight",
        "description": "Remove highlight overlay from DOM element.",
        "parameters_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "browser_annotate",
        "description": "Add annotation or commentary to current page view.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Annotation text to display"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "browser_resume",
        "description": "Resume paused execution or breakpoint in page.",
        "parameters_schema": {
            "type": "object",
            "properties": {}
        }
    },

    # ==========================================
    # PDF (--caps=pdf, 1 tool)
    # ==========================================
    {
        "name": "browser_pdf_save",
        "description": "Generate PDF document of current page with print media options.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to save PDF"},
                "format": {"type": "string", "description": "Paper format (e.g. A4, Letter)"},
                "landscape": {"type": "boolean", "description": "Print in landscape orientation"}
            }
        }
    },

    # ==========================================
    # Vision (--caps=vision, 6 tools)
    # ==========================================
    {
        "name": "browser_mouse_move_xy",
        "description": "Move mouse cursor to exact (x, y) coordinates.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "number", "description": "Horizontal coordinate in pixels"},
                "y": {"type": "number", "description": "Vertical coordinate in pixels"}
            },
            "required": ["x", "y"]
        }
    },
    {
        "name": "browser_mouse_click_xy",
        "description": "Click mouse button at exact (x, y) coordinates.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "number", "description": "Horizontal coordinate in pixels"},
                "y": {"type": "number", "description": "Vertical coordinate in pixels"},
                "button": {"type": "string", "enum": ["left", "right", "middle"], "description": "Mouse button"}
            },
            "required": ["x", "y"]
        }
    },
    {
        "name": "browser_mouse_drag_xy",
        "description": "Drag mouse from source (x, y) to target (x, y) coordinates.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "start_x": {"type": "number", "description": "Start X coordinate"},
                "start_y": {"type": "number", "description": "Start Y coordinate"},
                "end_x": {"type": "number", "description": "End X coordinate"},
                "end_y": {"type": "number", "description": "End Y coordinate"}
            },
            "required": ["start_x", "start_y", "end_x", "end_y"]
        }
    },
    {
        "name": "browser_mouse_down",
        "description": "Press down mouse button at current position.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "button": {"type": "string", "enum": ["left", "right", "middle"], "description": "Mouse button"}
            }
        }
    },
    {
        "name": "browser_mouse_up",
        "description": "Release mouse button at current position.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "button": {"type": "string", "enum": ["left", "right", "middle"], "description": "Mouse button"}
            }
        }
    },
    {
        "name": "browser_mouse_wheel",
        "description": "Dispatch mouse wheel scroll delta.",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "delta_x": {"type": "number", "description": "Horizontal scroll delta"},
                "delta_y": {"type": "number", "description": "Vertical scroll delta"}
            },
            "required": ["delta_y"]
        }
    },

    # ==========================================
    # Config (--caps=config, 1 tool)
    # ==========================================
    {
        "name": "browser_get_config",
        "description": "Retrieve current Playwright browser configuration, viewport, and active capabilities.",
        "parameters_schema": {
            "type": "object",
            "properties": {}
        }
    }
]
