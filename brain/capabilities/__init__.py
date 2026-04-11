"""Local capability tools for Nexus."""

def register_all_capabilities(mcp_manager):
    """Register all capability tools with the MCP manager."""
    from brain.capabilities import screenshot_ocr, active_window, clipboard_recall
    from brain.capabilities import browser_history, process_monitor, system_control
    from brain.capabilities import windows_notify, file_search, pdf_read, image_describe

    modules = [screenshot_ocr, active_window, clipboard_recall, browser_history,
               process_monitor, system_control, windows_notify, file_search,
               pdf_read, image_describe]

    for mod in modules:
        try:
            for tool in mod.get_tools():
                if tool["name"] not in mcp_manager.tools:
                    mcp_manager.tools[tool["name"]] = tool
        except Exception as e:
            import logging
            logging.getLogger("jarvis.capabilities").warning("Failed to load %s: %s", mod.__name__, e)
