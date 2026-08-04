# Debug Mode User Guide

## 📋 Overview
 
Debug mode provides complete AI conversation log output functionality, allowing you to see all raw responses and output results in the terminal.

## 🎯 Features

### 1. User Message Display
In debug mode, all messages sent by users will be displayed in the terminal:
```
================================================================================
[DEBUG] 👤 User Message:
Help me calculate what 1+1 equals
================================================================================
```

### 2. AI Reasoning Process Display
If the AI model supports reasoning functionality, the reasoning content will be displayed in real-time:
```
[DEBUG] 🧠 AI Reasoning: User wants a simple math calculation...
```

### 3. AI Real-time Response Display
AI responses will be displayed character by character in real-time in the terminal:
```
[DEBUG] 🤖 AI: 1+1 equals 2
[DEBUG] 🤖 AI: .
```

### 4. Conversation Loop Information
Display the current conversation round and loop status:
```
[DEBUG] 🔄 Starting conversation loop, max iterations: 5

[DEBUG] 📍 Round 1 conversation
```

### 5. Command Parsing and Execution
Display the parsing and execution process of AI-generated commands:
```
[DEBUG] 🔍 Parsing and executing command...

[DEBUG] 📋 Command execution result:
✓ Execution successful: execute_command
  Result: {"output": "2"}

Executed 1 command, 1 successful, 0 failed
```

### 6. Loop Status Tracking
Display the progress status and termination reason of the conversation loop:
```
[DEBUG] ✅ Conversation loop ended
```
or
```
[DEBUG] ⚠️ Reached maximum loop count 5, stopping
```

## 🔧 How to Enable

### Method 1: Configure in .env file

Edit the `.env` file and add or modify the following configuration:
```ini
# Enable Debug mode
DEBUG_MODE=true
```

### Method 2: Specify in command line parameters

Add the `--debug` parameter when running the program:
```bash
python src/main.py --debug
```

### Method 3: Configure in PowerShell script

Edit the `start_app.ps1` file and add to the runtime parameters:
```powershell
$env:DEBUG_MODE = "true"
```

## 📊 Output Examples

### Complete Conversation Flow

```
[DEBUG] 🔄 Starting conversation loop, max iterations: 5

[DEBUG] 📍 Round 1 conversation

================================================================================
[DEBUG] 👤 User Message:
Open browser and visit Baidu
================================================================================

[DEBUG] 🧠 AI Reasoning: User wants to open browser and visit Baidu, I need to check system permissions first...
[DEBUG] 🤖 AI: Okay, I'll help you open the browser and visit Baidu.
[DEBUG] 🤖 AI: First let me check the system permissions.
[DEBUG] 🤖 AI: <control>{"type": "get_system_info"}</control>

[DEBUG] 🔍 Parsing and executing command...

[DEBUG] 📋 Command execution result:
✓ Execution successful: get_system_info
  Result: {"screen_width": 1920, "screen_height": 1080, "permission": "full"}

Executed 1 command, 1 successful, 0 failed

[DEBUG] 📍 Round 2 conversation

[DEBUG] 🧠 AI Reasoning: Permission check passed, now executing browser open operation...
[DEBUG] 🤖 AI: Now I'll open the browser.
[DEBUG] 🤖 AI: <control>{"type": "execute_command", "command": "start msedge https://www.baidu.com"}</control>

[DEBUG] 🔍 Parsing and executing command...

[DEBUG] 📋 Command execution result:
✓ Execution successful: execute_command
  Result: {"output": ""}

Executed 1 command, 1 successful, 0 failed

[DEBUG] ✅ Conversation loop ended
```

## 🎨 Color Description

Debug output uses different colors to distinguish different types of information:

| Color | Description | Content |
|------|------|------|
| 🟢 Green | User Message | Original message sent by user |
| ⚪ Gray | AI Reasoning | AI's thinking process (if model supports) |
| 🔵 Blue | AI Response | AI's real-time response content |
| 🟡 Yellow | System Information | Loop status, command execution results, etc. |

## ⚙️ Configuration Options

### DEBUG_MODE
- **Type**: Boolean
- **Default**: false
- **Description**: Whether to enable debug mode
- **Possible values**: true, false

### Related Configuration
- **NO_COLOR**: Setting to any value will disable color output
- **LOG_LEVEL**: Log level (if logging is also enabled)

## 📝 Notes

1. **Performance Impact**: Debug mode increases terminal output and may slightly affect performance
2. **Log Files**: In debug mode, it's recommended to also enable log saving functionality (-nolog parameter will disable it)
3. **Production Environment**: In production environments, it's recommended to disable debug mode to reduce log output
4. **Color Support**: If the terminal doesn't support colors, output will automatically disable color formatting

## 🔍 Troubleshooting

### Issue: Cannot see color output
**Solution**:
- Check if terminal supports ANSI colors
- Ensure `NO_COLOR` environment variable is not set

### Issue: Cannot see debug output
**Solution**:
- Confirm `DEBUG_MODE=true` is correctly set
- Check if `.env` file is properly loaded
- Confirm program was started with `--debug` parameter

### Issue: Too much output to view
**Solution**:
- Use terminal scrolling to view historical output
- Redirect output to file: `python src/main.py --debug > debug.log 2>&1`
- Use log file saving functionality (enabled by default in debug mode)

## 💡 Best Practices

1. **Development Debugging**: Enable debug mode during development to facilitate viewing AI behavior
2. **Problem Diagnosis**: Enable debug mode when encountering issues to analyze AI decision-making process
3. **Performance Testing**: Disable debug mode during performance testing to reduce output impact
4. **Log Analysis**: Combine with log file analysis, debug output + log file dual recording