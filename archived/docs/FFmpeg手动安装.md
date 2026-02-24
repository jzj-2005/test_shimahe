# FFmpeg 手动安装指南

## 下载链接（选择一个）

**方法1：gyan.dev（推荐，官方推荐源）**
https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip

**方法2：GitHub Release**
https://github.com/BtbN/FFmpeg-Builds/releases

## 安装步骤

1. **下载**
   - 下载上面链接的 ffmpeg-release-essentials.zip（约100MB）

2. **解压**
   - 解压到 `C:\ffmpeg`
   - 确保路径是: `C:\ffmpeg\bin\ffmpeg.exe`

3. **添加到PATH（重要！）**
   
   **方法A：使用PowerShell（推荐）**
   ```powershell
   # 以管理员身份运行PowerShell，然后执行：
   [Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\ffmpeg\bin", "Machine")
   ```

   **方法B：手动设置**
   - 按 Win+R，输入: sysdm.cpl
   - 点击"高级" → "环境变量"
   - 在"系统变量"中找到"Path"，点击"编辑"
   - 点击"新建"，添加: `C:\ffmpeg\bin`
   - 点击"确定"保存所有窗口

4. **验证安装**
   - 打开**新的**PowerShell窗口
   - 运行: `ffmpeg -version`
   - 看到版本号就成功了

## 已经下载好的FFmpeg？

如果你已经有FFmpeg文件，直接运行：
```powershell
# 假设FFmpeg在 D:\tools\ffmpeg\bin
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";D:\tools\ffmpeg\bin", "Machine")
```

## 快速验证

```powershell
# 重新打开PowerShell后运行
ffmpeg -version
```

如果显示版本信息，就可以继续视频推理了！
