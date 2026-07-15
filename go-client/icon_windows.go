//go:build windows

package main

import (
	"bytes"
	"encoding/base64"
	"fmt"
	"image"
	"image/color"
	"image/png"
	"sync"
	"syscall"
	"unsafe"

	ole "github.com/go-ole/go-ole"
	"golang.org/x/sys/windows"
)

var (
	shell32  = windows.NewLazySystemDLL("shell32.dll")
	user32   = windows.NewLazySystemDLL("user32.dll")
	gdi32    = windows.NewLazySystemDLL("gdi32.dll")

	procSHGetFileInfo      = shell32.NewProc("SHGetFileInfoW")
	procDestroyIcon        = user32.NewProc("DestroyIcon")
	procGetIconInfo        = user32.NewProc("GetIconInfo")
	procCreateIcon         = user32.NewProc("CreateIcon")
	procDeleteObject       = gdi32.NewProc("DeleteObject")
	procGetDIBits          = gdi32.NewProc("GetDIBits")
	procGetDC              = user32.NewProc("GetDC")
	procReleaseDC          = user32.NewProc("ReleaseDC")
	procCreateCompatibleDC = gdi32.NewProc("CreateCompatibleDC")
	procDeleteDC           = gdi32.NewProc("DeleteDC")
	procSelectObject       = gdi32.NewProc("SelectObject")
	procGetObjectW         = gdi32.NewProc("GetObjectW")
)

const (
	shellGetIcon = 0x000000100 // SHGFI_ICON
	// SHGFI_LARGEICON = 0（默认大图标，无需额外位）
)

// SHFILEINFOW 结构（仅用到的字段）。
type shfileinfo struct {
	hIcon      uintptr
	iIcon      int32
	dwAttr     uint32
	szDispName [260]uint16
	szTypeName [80]uint16
}

// ICONINFO 结构。
type iconinfo struct {
	fIcon    int32
	xHotspot uint32
	yHotspot uint32
	hbmMask  uintptr
	hbmColor uintptr
}

// 进程级图标缓存：key = exePath/lnkPath，value = base64 PNG（或空串表示无图标）。
var iconCache sync.Map

// GetIconBase64 提取一个快捷方式的图标，返回 data:image/png;base64,... 字符串。
// 前端用 <img src> 直接渲染。命中缓存时 O(1)。
// 对应 Python icon_utils.shortcut_icon 的提取逻辑。
func (a *App) GetIconBase64(exePath, lnkPath, sourceType string) string {
	// 选取主目标：优先 exe，其次 lnk。
	target := exePath
	if target == "" {
		target = lnkPath
	}
	if target == "" {
		return ""
	}
	cacheKey := target
	if v, ok := iconCache.Load(cacheKey); ok {
		if s, _ := v.(string); s != "" {
			return s
		}
	}

	var dataURL string
	if sourceType == "uwp" && !looksLikeFilesystemPath(target) {
		// 真 UWP：通过 IShellItemImageFactory 提取。
		dataURL = uwpIconToBase64(target)
	}
	if dataURL == "" {
		// exe / lnk：通过 SHGetFileInfo 提取。
		dataURL = fileIconToBase64(target)
	}
	if dataURL == "" && lnkPath != "" && lnkPath != target {
		// 兜底：用 lnk 文件自身的图标。
		dataURL = fileIconToBase64(lnkPath)
	}
	if dataURL == "" {
		// 标记无图标，避免反复尝试。
		iconCache.Store(cacheKey, "")
		return ""
	}
	iconCache.Store(cacheKey, dataURL)
	return dataURL
}

// fileIconToBase64 用 SHGetFileInfo 提取 exe/lnk 的图标转 base64 PNG。
func fileIconToBase64(path string) string {
	hicon := extractHIcon(path)
	if hicon == 0 {
		return ""
	}
	defer procDestroyIcon.Call(hicon)
	pngBytes, err := hiconToPNG(hicon, 32)
	if err != nil {
		lastSHGetFileError = "hiconToPNG: " + err.Error()
		return ""
	}
	return "data:image/png;base64," + base64.StdEncoding.EncodeToString(pngBytes)
}

// extractHIcon 调 SHGetFileInfoW 获取大图标 HICON。
func extractHIcon(path string) uintptr {
	pPath, _ := windows.UTF16PtrFromString(path)
	var fi shfileinfo
	flags := uintptr(shellGetIcon) // SHGFI_ICON（隐含 LARGEICON）
	// SHGetFileInfoW(pszPath, dwFileAttributes, psfi, cbFileInfo, uFlags)
	ret, _, lastErr := procSHGetFileInfo.Call(
		uintptr(unsafe.Pointer(pPath)),
		0,
		uintptr(unsafe.Pointer(&fi)),
		unsafe.Sizeof(fi),
		flags,
	)
	if ret == 0 {
		// 调试用：记录失败原因。
		lastSHGetFileError = "ret=0 lastErr=" + lastErr.Error()
		return 0
	}
	if fi.hIcon == 0 {
		lastSHGetFileError = fmt.Sprintf("ret=%d 但 hIcon=0（可能 flags 或结构布局问题）", ret)
		return 0
	}
	return fi.hIcon
}

// 保存最近一次 SHGetFileInfo 失败信息，供测试/调试。
var lastSHGetFileError string

// hiconToPNG 将 HICON 转换为 PNG 字节（指定目标尺寸）。
// 链路：GetIconInfo → 取色位图 → GetDIBits 读像素 → image.RGBA → png.Encode。
func hiconToPNG(hicon uintptr, size int) ([]byte, error) {
	var ii iconinfo
	ret, _, _ := procGetIconInfo.Call(hicon, uintptr(unsafe.Pointer(&ii)))
	if ret == 0 {
		return nil, fmt.Errorf("GetIconInfo 失败")
	}
	// 释放 mask 位图，color 位图交给 GetDIBits 用完再删。
	if ii.hbmMask != 0 {
		procDeleteObject.Call(ii.hbmMask)
	}
	hbmColor := ii.hbmColor
	if hbmColor == 0 {
		return nil, fmt.Errorf("无色位图")
	}
	defer procDeleteObject.Call(hbmColor)

	// 读取位图尺寸。Win32 BITMAP 结构：bmType/bmWidth/bmHeight/bmWidthBytes(LONG×4)
	// + bmPlanes/bmBitsPixel(WORD×2) + bmBits(LPVOID) = 28 字节（64位）。
	var bmp struct {
		bmType       int32
		bmWidth      int32
		bmHeight     int32
		bmWidthBytes int32
		bmPlanes     uint16
		bmBitsPixel  uint16
		bmBits       uintptr
	}
	procGetObjectW.Call(hbmColor, unsafe.Sizeof(bmp), uintptr(unsafe.Pointer(&bmp)))

	srcW := int(bmp.bmWidth)
	srcH := int(bmp.bmHeight)
	// icon 位图高度是宽度的 2 倍（含 mask），色位图高度正常。
	iconH := srcH
	if iconH > srcW*2 {
		iconH = srcH / 2
	}
	// 尺寸为零保护：GetObjectW 失败或异常位图时直接放弃。
	if srcW <= 0 || iconH <= 0 {
		return nil, fmt.Errorf("位图尺寸异常 %dx%d", srcW, iconH)
	}

	// 准备 BITMAPINFO 请求 32 位 BGRA 像素。
	var bi struct {
		biSize          uint32
		biWidth         int32
		biHeight        int32
		biPlanes        uint16
		biBitCount      uint16
		biCompression   uint32
		biSizeImage     uint32
		biXPelsPerMeter int32
		biYPelsPerMeter int32
		biClrUsed       uint32
		biClrImportant  uint32
	}
	bi.biSize = uint32(unsafe.Sizeof(bi))
	bi.biWidth = int32(srcW)
	bi.biHeight = int32(iconH) // 正数 = 自下而上
	bi.biPlanes = 1
	bi.biBitCount = 32
	bi.biCompression = 0 // BI_RGB

	pixelLen := srcW * iconH * 4
	pixels := make([]byte, pixelLen)

	hdc, _, _ := procGetDC.Call(0)
	defer procReleaseDC.Call(0, hdc)
	hdcMem, _, _ := procCreateCompatibleDC.Call(hdc)
	defer procDeleteDC.Call(hdcMem)
	procSelectObject.Call(hdcMem, hbmColor)

	ok, _, _ := procGetDIBits.Call(
		hdcMem,
		hbmColor,
		0,
		uintptr(iconH),
		uintptr(unsafe.Pointer(&pixels[0])),
		uintptr(unsafe.Pointer(&bi)),
		0, // DIB_RGB_COLORS
	)
	if ok == 0 {
		return nil, fmt.Errorf("GetDIBits 失败")
	}

	// BGRA → RGBA，构建 image.RGBA。
	img := image.NewRGBA(image.Rect(0, 0, srcW, iconH))
	for y := 0; y < iconH; y++ {
		for x := 0; x < srcW; x++ {
			off := (y*srcW + x) * 4
			b := pixels[off]
			g := pixels[off+1]
			r := pixels[off+2]
			a := pixels[off+3]
			// 自下而上 → 翻转 y。
			dstY := iconH - 1 - y
			di := (dstY*srcW + x) * 4
			// 若 alpha 为 0，背景透明即可；否则预乘处理由 PNG 自带 alpha 表达。
			img.Pix[di] = r
			img.Pix[di+1] = g
			img.Pix[di+2] = b
			img.Pix[di+3] = a
		}
	}

	// 缩放到目标尺寸（若不同）。
	final := image.Image(img)
	if srcW != size || iconH != size {
		final = resizeNearest(img, srcW, iconH, size, size)
	}

	var buf bytes.Buffer
	if err := png.Encode(&buf, final); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}

// resizeNearest 最近邻缩放（图标小，质量足够且快速）。
func resizeNearest(src *image.RGBA, sw, sh, dw, dh int) *image.RGBA {
	dst := image.NewRGBA(image.Rect(0, 0, dw, dh))
	sx := float64(sw) / float64(dw)
	sy := float64(sh) / float64(dh)
	for y := 0; y < dh; y++ {
		for x := 0; x < dw; x++ {
			si := (int(float64(y)*sy)*sw + int(float64(x)*sx)) * 4
			di := (y*dw + x) * 4
			if si+3 < len(src.Pix) {
				dst.Pix[di] = src.Pix[si]
				dst.Pix[di+1] = src.Pix[si+1]
				dst.Pix[di+2] = src.Pix[si+2]
				dst.Pix[di+3] = src.Pix[si+3]
			}
		}
	}
	return dst
}

// uwpIconToBase64 通过 IShellItemImageFactory 提取 UWP 应用图标。
// 对应 Python _icon_from_shell_app_id。
func uwpIconToBase64(appID string) string {
	parseName := "shell:AppsFolder\\" + appID

	ole.CoInitializeEx(0, ole.COINIT_APARTMENTTHREADED)
	defer ole.CoUninitialize()

	// SHCreateItemFromParsingName 需要 shell32，但 go-ole 不直接暴露。
	// 用 Shell.Application 的 Namespace + Items 难拿位图。
	// 改用 IShellItemImageFactory：通过 CoCreateInstance 创建，或用 SHCreateItemFromParsingName。
	// 这里用 syscall 直接调 SHCreateItemFromParsingName。
	pName, _ := windows.UTF16PtrFromString(parseName)

	// IID_IShellItem: 43826d1e-e718-42ee-bc55-a1e268c37e95
	shellItemIID := syscall.GUID{Data1: 0x43826d1e, Data2: 0xe718, Data3: 0x42ee, Data4: [8]byte{0xbc, 0x55, 0xa1, 0xe2, 0x68, 0xc3, 0x7e, 0x95}}
	// IID_IShellItemImageFactory: bcc18b79-ba16-442f-80c4-8a59c30c463b
	factoryIID := syscall.GUID{Data1: 0xbcc18b79, Data2: 0xba16, Data3: 0x442f, Data4: [8]byte{0x80, 0xc4, 0x8a, 0x59, 0xc3, 0x04, 0x63, 0x3b}}

	procSHCreateItemFromParsingName := shell32.NewProc("SHCreateItemFromParsingName")
	var shellItem uintptr
	hr, _, _ := procSHCreateItemFromParsingName.Call(
		uintptr(unsafe.Pointer(pName)),
		0,
		uintptr(unsafe.Pointer(&shellItemIID)),
		uintptr(unsafe.Pointer(&shellItem)),
	)
	if hr != 0 || shellItem == 0 {
		return ""
	}
	defer iunknownRelease(shellItem)

	// QueryInterface 拿 IShellItemImageFactory —— 直接通过 IUnknown vtable[0] 调用，
	// 因为 go-ole 的 QueryInterface 强制返回 *IDispatch，不适合非自动化接口。
	var factory uintptr
	qiAddr := iunknownVtable(shellItem, 0) // QueryInterface = vtable[0]
	hr, _, _ = syscall.Syscall6(qiAddr, 4,
		shellItem,
		uintptr(unsafe.Pointer(&factoryIID)),
		uintptr(unsafe.Pointer(&factory)),
		0, 0, 0,
	)
	if hr != 0 || factory == 0 {
		return ""
	}
	defer iunknownRelease(factory)

	// GetImage(size, flags, *hbitmap) —— vtable 第 4 个方法（索引 3）。
	// flags = SIIGBF_ICONONLY(0x1) | SIIGBF_BIGGERSIZEOK(0x4) = 0x5
	const siigbf = 0x5
	var hbitmap uintptr
	getImageAddr := iunknownVtable(factory, 3)
	type sizeT struct{ CX, CY int32 }
	sz := sizeT{CX: 48, CY: 48}
	hr, _, _ = syscall.Syscall6(getImageAddr, 4,
		factory,
		uintptr(unsafe.Pointer(&sz)),
		uintptr(siigbf),
		uintptr(unsafe.Pointer(&hbitmap)),
		0, 0,
	)
	if hr != 0 || hbitmap == 0 {
		return ""
	}
	defer procDeleteObject.Call(hbitmap)

	pngBytes, err := hbitmapToPNG(hbitmap)
	if err != nil {
		return ""
	}
	return "data:image/png;base64," + base64.StdEncoding.EncodeToString(pngBytes)
}

// iunknownVtable 取 COM 对象 vtable 中第 index 个方法地址。
// COM 对象首字段是指向 vtable 的指针，vtable 前 3 项是 IUnknown 方法。
// 用 uintptr 数组指针模式读取，符合 go vet 对 unsafe 的检查规则。
func iunknownVtable(comObj uintptr, index int) uintptr {
	// comObj 首字段 -> vtable 指针。
	vtablePtr := *(**[1 << 16]uintptr)(unsafe.Pointer(comObj))
	return vtablePtr[index]
}

// iunknownRelease 调用 IUnknown::Release（vtable[2]）。
func iunknownRelease(comObj uintptr) {
	releaseAddr := iunknownVtable(comObj, 2)
	syscall.Syscall(releaseAddr, 1, comObj, 0, 0)
}

// hbitmapToPNG 将 HBITMAP（32位 BGRA）转为 PNG。
func hbitmapToPNG(hbm uintptr) ([]byte, error) {
	var bmp struct {
		bmType       int32
		bmWidth      int32
		bmHeight     int32
		bmWidthBytes int32
		bmPlanes     uint16
		bmBitsPixel  uint16
		bmBits       uintptr
	}
	procGetObjectW.Call(hbm, unsafe.Sizeof(bmp), uintptr(unsafe.Pointer(&bmp)))
	if bmp.bmWidth == 0 || bmp.bmHeight == 0 {
		return nil, fmt.Errorf("空位图")
	}
	w := int(bmp.bmWidth)
	h := int(bmp.bmHeight)

	var bi struct {
		biSize          uint32
		biWidth         int32
		biHeight        int32
		biPlanes        uint16
		biBitCount      uint16
		biCompression   uint32
		biSizeImage     uint32
		biXPelsPerMeter int32
		biYPelsPerMeter int32
		biClrUsed       uint32
		biClrImportant  uint32
	}
	bi.biSize = uint32(unsafe.Sizeof(bi))
	bi.biWidth = int32(w)
	bi.biHeight = int32(h)
	bi.biPlanes = 1
	bi.biBitCount = 32

	pixels := make([]byte, w*h*4)
	hdc, _, _ := procGetDC.Call(0)
	defer procReleaseDC.Call(0, hdc)
	hdcMem, _, _ := procCreateCompatibleDC.Call(hdc)
	defer procDeleteDC.Call(hdcMem)
	procSelectObject.Call(hdcMem, hbm)
	ok, _, _ := procGetDIBits.Call(hdcMem, hbm, 0, uintptr(h), uintptr(unsafe.Pointer(&pixels[0])), uintptr(unsafe.Pointer(&bi)), 0)
	if ok == 0 {
		return nil, fmt.Errorf("GetDIBits 失败")
	}

	img := image.NewRGBA(image.Rect(0, 0, w, h))
	for y := 0; y < h; y++ {
		for x := 0; x < w; x++ {
			off := (y*w + x) * 4
			b := pixels[off]
			g := pixels[off+1]
			r := pixels[off+2]
			a := pixels[off+3]
			dstY := h - 1 - y
			di := (dstY*w + x) * 4
			img.Pix[di] = r
			img.Pix[di+1] = g
			img.Pix[di+2] = b
			img.Pix[di+3] = a
		}
	}
	_ = color.RGBAModel
	var buf bytes.Buffer
	if err := png.Encode(&buf, img); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}
