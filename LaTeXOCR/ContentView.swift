//
//  ContentView.swift
//  LaTeXOCR
//
//  Created by 颜家俊 on 2024/10/20.
//

import SwiftUI
import AppKit
import WebKit

struct ContentView: View {
    @State private var image: NSImage? = nil
    @State private var latexFormula: String = ""
    @State private var savedImageURL: URL? // New state to store the URL of the saved image
    @State private var image_base64String: String = "" // 新增状态变量存储Base64编码字符串
    
    var body: some View {
        VStack {
            // TOP SECTION - Split into left and right
            HStack {
                // Left side - Image display area
                VStack {
                    if let image = image {
                        Image(nsImage: image)
                            .resizable()
                            .scaledToFit()
                            .frame(height: 300)
                    } else {
                        Rectangle()
                            .fill(Color.gray)
                            .frame(height: 300)
                            .overlay(Text("No Image Selected"))
                    }
                }
                .frame(width: 300)
                .border(Color.gray)
                .cornerRadius(4)
                
                // Right side - Empty area for future use
                VStack {
                    Text("公式预览")
                        .font(.headline)
                        .padding(.bottom, 5)
                    
                    // 这里不再指定固定宽度，允许KaTeXView自适应
                    KaTeXView(latexFormula: latexFormula, requestToken: 0)
                        .frame(height: 260)
                }
                .frame(minWidth: 200)
                .cornerRadius(4)
            }
            .padding()
            .cornerRadius(4)
            
            // BOTTOM SECTION
            VStack {
                Button("转换公式") {
                    convertImageToLatex()
                }
                .padding()
                
                TextField("输入或显示LaTeX公式", text: $latexFormula)
                    .font(.system(size: 14, weight: .regular, design: .monospaced))
                    .padding()
                    .background(Color(.textBackgroundColor))
                    .cornerRadius(4)
            }
            .padding()
        }
        .padding()
        .onAppear {
            // 监听截图通知
            NotificationCenter.default.addObserver(
                forName: Notification.Name("TriggerScreenshot"),
                object: nil,
                queue: .main
            ) { _ in
                startScreenshotProcess()
            }
        }
    }
    
    private func startScreenshotProcess() {
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
                    loadImage(from: screenshotPath)
                    convertImageToLatex()
                }
            }
        } catch {
            // Handle errors and notify the user
            print("Error executing screencapture: \(error.localizedDescription)")
            DispatchQueue.main.async {
                // Optionally inform the user with a dialog or other UI update
                latexFormula = "Error capturing screenshot: \(error.localizedDescription)"
            }
        }
    }
    
    private func loadImage(from path: String) {
        if let screenshotImage = NSImage(contentsOfFile: path) {
            self.image = screenshotImage
            self.image_base64String = convertImageToBase64(image: screenshotImage) ?? "Failed to encode image"
        }
    }
    
    private func convertImageToBase64(image: NSImage) -> String? {
        guard let tiffData = image.tiffRepresentation,
              let bitmapImage = NSBitmapImageRep(data: tiffData),
              let pngData = bitmapImage.representation(using: .png, properties: [:]) else {
            return nil
        }
        return pngData.base64EncodedString(options: .lineLength64Characters)
    }
    
    private func convertImageToLatex() {
        // OCR到LaTeX转换的虚拟实现
        let result = ocrFormulaToLatex(imageBase64: self.image_base64String)
        self.latexFormula = result
        NSPasteboard.general.clearContents()
        let formatToUse = preferredCopyFormat()
        if formatToUse == "mathml" {
            print("MathML copy not available in ContentView; falling back to LaTeX.")
        }
        NSPasteboard.general.setString(result, forType: .string)
        
        // 复制到剪贴板后，图标跳动一下
        NSApp.requestUserAttention(.informationalRequest)
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
    
    func ocrFormulaToLatex(imageBase64: String) -> String {
        guard let config = loadAPIConfig() else {
            return ""
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
                print("Error: \(error.localizedDescription)")
                return
            }
            
            guard let data = data else {
                print("No data received")
                return
            }
            
            do {
                if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let choices = json["choices"] as? [[String: Any]],
                   let firstChoice = choices.first,
                   let message = firstChoice["message"] as? [String: Any],
                   let content = message["content"] as? String {
                    resultString = removeLatexMarkers(from: content)
                }
            } catch {
                print("JSON parsing error: \(error.localizedDescription)")
            }
        }
        
        task.resume()
        semaphore.wait()
        
        return resultString
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
    
    private func preferredCopyFormat() -> String {
        let format = UserDefaults.standard.string(forKey: "copyFormat")?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? "latex"
        return format.isEmpty ? "latex" : format
    }
}

//#Preview {
//    ContentView()
//}
