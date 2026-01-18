//
//  IdentifyProcess.swift
//  LaTeXOCR
//
//  Created by 颜家俊 on 2025/4/14.
//

import Foundation
import SwiftUI

// 主识别处理类
class IdentifyProcess: ObservableObject {
    // 可观察属性
    @Published var latexFormula: String = ""
    @Published var mathmlFormula: String = ""
    @Published private(set) var image: NSImage? = nil
    @Published var isLoading: Bool = false
    @Published var pendingMathMLCopy: Bool = false
    @Published var pendingCopyFeedback: Bool = false
    @Published var copyFeedbackMessage: String = ""
    private var copyFeedbackWorkItem: DispatchWorkItem?
    
    private var savedImageURL: URL? // New state to store the URL of the saved image
    private var image_base64String: String = "" // 新增状态变量存储Base64编码字符串

    func copyLatexCode() {
        _ = copyStringToPasteboard(self.latexFormula, isMathML: false)
        // 复制到剪贴板后，让程序图标跳动一下提示用户
        NSApp.requestUserAttention(.informationalRequest)
    }
    
    func copyLatexWithFeedback() {
        if latexFormula.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            showCopyFeedback("暂无公式可复制")
            return
        }
        if copyFormulaCode(copyFormula: "latex") {
            showCopyFeedback("已复制 LaTeX")
        } else {
            showCopyFeedback("复制失败")
        }
    }
    func copyFormulaCode(copyFormula:String) -> Bool {
        let formatToUse = copyFormula.isEmpty ? preferredCopyFormat() : copyFormula
        if formatToUse == "latex" {
            return copyStringToPasteboard(self.latexFormula, isMathML: false)
        }else if formatToUse == "mathml" {
            return copyStringToPasteboard(self.mathmlFormula, isMathML: true)
        }
        // 复制到剪贴板后，让程序图标跳动一下提示用户
        NSApp.requestUserAttention(.informationalRequest)
        return false
    }
    
    func ocrFormulaToLatex(imageBase64: String) -> String {
        guard let config = loadAPIConfig() else {
            return "Missing API settings. Please configure them in Settings."
        }
        
        var request = URLRequest(url: config.url)
        request.httpMethod = "POST"
        request.addValue("Bearer \(config.apiKey)", forHTTPHeaderField: "Authorization")
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let requestBody: [String: Any] = [
            "model": config.model,
            "messages": [
                [
                    "role": "user",
                    "content": [
                        [
                            "type": "text",
                            "text": "Please transcribe it into LaTeX format. please only return LaTeX formula without any other unuseful symbol, so I can patse it to my doc directly."
                        ],
                        [
                            "type": "image_url",
                            "image_url": [
                                "url": "data:image/jpeg;base64,\(imageBase64)"
                            ]
                        ]
                    ]
                ]
            ]
        ]
        
        request.httpBody = try? JSONSerialization.data(withJSONObject: requestBody)
        
        let semaphore = DispatchSemaphore(value: 0)
        var resultString = ""
        
        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            defer { semaphore.signal() }
            
            if let error = error {
                let message = "Network error: \(error.localizedDescription)"
                print(message)
                resultString = message
                return
            }
            
            guard let data = data else {
                let message = "No data received from API."
                print(message)
                resultString = message
                return
            }
            
            do {
                if let httpResponse = response as? HTTPURLResponse,
                   !(200...299).contains(httpResponse.statusCode) {
                    let body = String(data: data, encoding: .utf8) ?? ""
                    let message = "API error (\(httpResponse.statusCode)): \(body)"
                    print(message)
                    resultString = message
                    return
                }
                if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let choices = json["choices"] as? [[String: Any]],
                   let firstChoice = choices.first,
                   let message = firstChoice["message"] as? [String: Any],
                   let content = message["content"] as? String {
                    resultString = self.removeLatexMarkers(from: content)
                } else {
                    let message = "Unexpected API response."
                    print(message)
                    resultString = message
                }
            } catch {
                let message = "JSON parsing error: \(error.localizedDescription)"
                print(message)
                resultString = message
            }
        }
        
        task.resume()
        semaphore.wait()
        
        return resultString
    }
    
    func removeLatexMarkers(from string: String) -> String {
        let pattern = "```latex\\n|```"
        let regex = try! NSRegularExpression(pattern: pattern, options: [])
        let range = NSRange(string.startIndex..., in: string)
        let cleanedString = regex.stringByReplacingMatches(in: string, options: [], range: range, withTemplate: "")
        let trimmed = cleanedString.trimmingCharacters(in: .whitespacesAndNewlines)
        return stripDisplayMathDelimiters(from: trimmed)
    }
    
    private func stripDisplayMathDelimiters(from string: String) -> String {
        if string.hasPrefix("\\[") && string.hasSuffix("\\]") {
            let start = string.index(string.startIndex, offsetBy: 2)
            let end = string.index(string.endIndex, offsetBy: -2)
            return String(string[start..<end]).trimmingCharacters(in: .whitespacesAndNewlines)
        }
        if string.hasPrefix("$$") && string.hasSuffix("$$") {
            let start = string.index(string.startIndex, offsetBy: 2)
            let end = string.index(string.endIndex, offsetBy: -2)
            return String(string[start..<end]).trimmingCharacters(in: .whitespacesAndNewlines)
        }
        return string
    }
    
    private func loadAPIConfig() -> (url: URL, apiKey: String, model: String)? {
        let urlString = UserDefaults.standard.string(forKey: "apiBaseURL")?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let apiKey = UserDefaults.standard.string(forKey: "apiKey")?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let selectedModel = UserDefaults.standard.string(forKey: "apiModel")?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? "gpt-5.2"
        let customModel = UserDefaults.standard.string(forKey: "apiModelCustom")?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let model = selectedModel == "其他" ? customModel : selectedModel
        
        guard !urlString.isEmpty, !apiKey.isEmpty else {
            print("Missing API settings. Please configure them in Settings.")
            return nil
        }
        
        if model.isEmpty {
            print("Missing model setting. Please configure it in Settings.")
            return nil
        }
        
        guard let url = URL(string: urlString) else {
            print("Invalid API URL in Settings.")
            return nil
        }
        
        return (url, apiKey, model)
    }
    
    func startScreenshotProcess() {
        // Ensure previous image is cleared
        self.image = nil
        
        // 获取应用程序支持目录
        guard let appSupportDir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first else {
            print("Unable to access Application Support directory")
            return
        }
        
        // 创建应用专用文件夹
        let appDir = appSupportDir.appendingPathComponent(Bundle.main.bundleIdentifier ?? "LaTeXOCR")
        
        do {
            try FileManager.default.createDirectory(at: appDir, withIntermediateDirectories: true, attributes: nil)
        } catch {
            print("Error creating app directory: \(error.localizedDescription)")
            return
        }
        // 设置截图路径
        let screenshotPath = appDir.appendingPathComponent("ocrPicture.png").path
        print(screenshotPath)
        let task = Process()
        task.launchPath = "/usr/sbin/screencapture"
        task.arguments = ["-i", screenshotPath]
        do {
            try task.run() // Try to run the task
            task.terminationHandler = { _ in
                DispatchQueue.main.async {
                    self.loadImage(from: screenshotPath)
                    self.convertImageToLatex()
                }
            }
        } catch {
            // Handle errors and notify the user
            print("Error executing screencapture: \(error.localizedDescription)")
            DispatchQueue.main.async {
                // Optionally inform the user with a dialog or other UI update
                self.latexFormula = "Error capturing screenshot: \(error.localizedDescription)"
            }
        }
    }
    
    func loadImage(from path: String) {
        if let screenshotImage = NSImage(contentsOfFile: path) {
            self.image = screenshotImage
            self.image_base64String = convertImageToBase64(image: screenshotImage) ?? "Failed to encode image"
        }
    }
    
    func convertImageToBase64(image: NSImage) -> String? {
        guard let tiffData = image.tiffRepresentation,
              let bitmapImage = NSBitmapImageRep(data: tiffData),
              let pngData = bitmapImage.representation(using: .png, properties: [:]) else {
            return nil
        }
        return pngData.base64EncodedString(options: .lineLength64Characters)
    }
    func convertImageToLatex() {
        isLoading = true
        let base64String = self.image_base64String
        DispatchQueue.global(qos: .userInitiated).async {
            let result = self.ocrFormulaToLatex(imageBase64: base64String)
            DispatchQueue.main.async {
                self.latexFormula = result
                let formatToUse = self.preferredCopyFormat()
                if formatToUse == "mathml" {
                    self.mathmlFormula = ""
                    self.pendingMathMLCopy = true
                    self.pendingCopyFeedback = false
                } else {
                    self.pendingMathMLCopy = false
                    self.pendingCopyFeedback = false
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(result, forType: .string)
                }
                self.isLoading = false
                
                // 复制到剪贴板后，图标跳动一下
                if formatToUse == "latex" {
                    NSApp.requestUserAttention(.informationalRequest)
                }
            }
        }
    }
    
    // 直接调用requestMathML函数并更新mathmlFormula变量
    func requestAndUpdateMathML(coordinator: KaTeXView.Coordinator) {
        coordinator.requestMathML()
        // 注意：实际的mathmlFormula更新是在KaTeXView的回调中完成的
        // 该方法只是触发了requestMathML的调用
    }
    
    func completeMathMLCopyIfNeeded() {
        if pendingMathMLCopy, !mathmlFormula.isEmpty {
            let success = copyFormulaCode(copyFormula: "mathml")
            if pendingCopyFeedback {
                showCopyFeedback(success ? "已复制 MathML(word)" : "复制失败")
            }
            pendingMathMLCopy = false
            pendingCopyFeedback = false
        }
    }
    
    func showCopyFeedback(_ message: String) {
        copyFeedbackWorkItem?.cancel()
        copyFeedbackMessage = message
        let workItem = DispatchWorkItem { [weak self] in
            self?.copyFeedbackMessage = ""
        }
        copyFeedbackWorkItem = workItem
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5, execute: workItem)
    }
    
    private func preferredCopyFormat() -> String {
        let format = UserDefaults.standard.string(forKey: "copyFormat")?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? "latex"
        return format.isEmpty ? "latex" : format
    }
    
    private func copyStringToPasteboard(_ content: String, isMathML: Bool) -> Bool {
        let trimmed = content.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            return false
        }
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        let item = NSPasteboardItem()
        item.setString(trimmed, forType: .string)
        if isMathML {
            item.setString(trimmed, forType: NSPasteboard.PasteboardType("public.mathml"))
            let htmlString = "<html><body>\(trimmed)</body></html>"
            if let htmlData = htmlString.data(using: .utf8) {
                item.setData(htmlData, forType: .html)
            }
        }
        return pasteboard.writeObjects([item])
    }
}
