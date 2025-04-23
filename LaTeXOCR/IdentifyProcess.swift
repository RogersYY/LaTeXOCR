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
    
    private var savedImageURL: URL? // New state to store the URL of the saved image
    private var image_base64String: String = "" // 新增状态变量存储Base64编码字符串
    private var defaultFormulaFormat: String = "latex" //mathml
    
    
    func copyLatexCode() {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(self.latexFormula, forType: .string)
        // 复制到剪贴板后，让程序图标跳动一下提示用户
        NSApp.requestUserAttention(.informationalRequest)
    }
    func copyFormulaCode(copyFormula:String) {
        let formatToUse = copyFormula.isEmpty ? self.defaultFormulaFormat : copyFormula
        NSPasteboard.general.clearContents()
        if formatToUse == "latex" {
            NSPasteboard.general.setString(self.latexFormula, forType: .string)
        }else if formatToUse == "mathml" {
            NSPasteboard.general.setString(self.mathmlFormula, forType:.string)
        }
        // 复制到剪贴板后，让程序图标跳动一下提示用户
        NSApp.requestUserAttention(.informationalRequest)
    }
    
    func ocrFormulaToLatex(imageBase64: String) -> String {
        let url = URL(string: "https://api.openai-hub.com/v1/chat/completions")!
        let apiKey = "sk-xMa3WlXiznsdngEYVjnGGU0hY3uAt2uy2RZ5V99sVXlIF7ek"
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let requestBody: [String: Any] = [
            "model": "gpt-4o-2024-11-20",
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
                    resultString = self.removeLatexMarkers(from: content)
                }
            } catch {
                print("JSON parsing error: \(error.localizedDescription)")
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
        return cleanedString.trimmingCharacters(in: .whitespacesAndNewlines)
    }
    
    func loginSCUNET(){
        guard let url = URL(string: "http://192.168.2.135/eportal/InterFace.do?method=login") else {
            print("Invalid SCUNET URL")
            return
        }
        // 定义请求
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        
        // 定义请求体
        let parameters: [String: String] = [
            "userId": "2023323040027",
            "password": "151836",
            "service": "internet",
            "queryString": "wlanuserip%3D1d203eecf62c8bb2ea695a7c92b03797%26wlanacname%3Dc71e94097544a7685edbb05cfb9628ae%26ssid%3D%26nasip%3Dd7a73fb5c210304203a602216e5d5e4e%26snmpagentip%3D%26mac%3Dc90ab37f2b3815ad0553ce7da940cd45%26t%3Dwireless-v2%26url%3Dc862a5edcc190c2edb16650375e6ef4e9108e97851c24226%26apmac%3D%26nasid%3Dc71e94097544a7685edbb05cfb9628ae%26vid%3Da52ba08d90c6999c%26port%3D41d73e29c1aa12a4%26nasportid%3D311e2b5a2ef217b48e5e93f1ce76a36c309ca59add64f2060c68f0bf7ec4ab80",
            "operatorPwd": "",
            "operatorUserId": "",
            "validcode": "",
            "passwordEncrypt": "false"
        ]
        let postData = parameters.map { "\($0.key)=\($0.value)" }.joined(separator: "&")
        request.httpBody = postData.data(using: .utf8)
        // 创建 URLSession
        let session = URLSession.shared
        // 发送请求
        let task = session.dataTask(with: request) { data, response, error in
            // 检查错误
            if let error = error {
                print("Error: \(error.localizedDescription)")
                return
            }
            
            // 检查响应数据
            if let data = data, let responseString = String(data: data, encoding: .utf8) {
                print("Response: \(responseString)")
            } else {
                print("No response data received.")
            }
        }
        
        // 启动任务
        task.resume()
        return
        
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
        // OCR到LaTeX转换的虚拟实现
        let result = ocrFormulaToLatex(imageBase64: self.image_base64String)
        self.latexFormula = result
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(result, forType: .string)
        
        // 复制到剪贴板后，图标跳动一下
        NSApp.requestUserAttention(.informationalRequest)
    }
}
