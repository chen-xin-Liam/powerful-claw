# User Manual

## Overview

AI Computer Control is an AI-powered automation application that allows you to control your computer using natural language commands.

## Getting Started

### 1. 启动应用程序

```bash
python src/ui/customtkinter_app.py
```

或者使用主入口：

```bash
python src/main.py
```

### 2. Set Permission Level

In the sidebar, select the appropriate permission level:

- **None**: View only, no system control
- **View**: Same as None
- **Limited**: Allows mouse movement, clicks, and keyboard input
- **Full**: All operations including hotkeys and window control

### 3. Choose Mode

- **Chat Mode**: Regular conversation with AI
- **Control Mode**: AI can generate system operations

## Basic Usage

### Chat Mode

1. Type your message in the chat input
2. Click "Send" or press Enter
3. View the AI's response

### Control Mode

1. Switch to Control Mode in the sidebar
2. Ask the AI to perform a task (e.g., "Open Notepad and type 'Hello World'")
3. If the AI generates operations, click "Execute Operations" to run them

## Available Operations

### Mouse Control
- Move mouse to specific coordinates
- Click at current position or specific coordinates
- Drag from one position to another

### Keyboard Control
- Type text
- Press single keys
- Execute hotkey combinations

### Screen Capture
- Click "Capture Screen" in the sidebar to take a screenshot

### Camera Access
- Click "Toggle Camera" to enable/disable camera

## Example Commands

```
"Move mouse to position (100, 200)"
"Click at current mouse position"
"Type 'Hello, World!' in the active window"
"Press Ctrl+C to copy"
"Open a browser and navigate to google.com"
```

## Safety Features

### Failsafe
- Move the mouse to the top-left corner of the screen to abort any running operation
- This is enabled by default for safety

### Permission Control
- Always check the permission level before executing operations
- Start with Limited permission before granting Full control

## Tips

1. **Be Specific**: Provide clear instructions for the AI
2. **Start Small**: Begin with simple tasks before complex operations
3. **Monitor Execution**: Watch the execution log for feedback
4. **Use Caution**: AI may make mistakes, always supervise operations

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+C | Copy |
| Ctrl+V | Paste |
| Ctrl+Z | Undo |
| Esc | Cancel current operation |

## Support

If you encounter issues or have questions:
1. Check the execution log for error messages
2. Verify your API key is correctly set
3. Ensure all dependencies are installed