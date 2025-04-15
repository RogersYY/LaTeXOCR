//
//  MainBoardView.swift
//  LaTeXOCR
//
//  Created by 颜家俊 on 2025/4/14.
//

import SwiftUI

struct MainBoardView: View {
//    @State private var image: NSImage? = nil
    //    @State private var latexFormula: String = ""
//    @State private var savedImageURL: URL? // New state to store the URL of the saved image
//    @State private var image_base64String: String = "" // 新增状态变量存储Base64编码字符串
    // 添加 IdentifyProcess 实例
    @StateObject private var identifyProcess = IdentifyProcess()
    
    var body: some View {
        VStack {
            HStack {
                
                if let image = identifyProcess.image {
                    VStack {
                        Text("识别图片")
                            .font(.headline)
                            .padding(.bottom, 5)
                        
                        Image(nsImage: image)
                            .resizable()
                            .scaledToFit()
                            .frame(height: 100)
                    }
                    .frame(width: 300)
                    .cornerRadius(4)
                }
                
                // Right side - Empty area for future use
                VStack {
                    Text("公式预览")
                        .font(.headline)
                        .padding(.bottom, 5)
                    
                    KaTeXView(latexFormula: identifyProcess.latexFormula)
                        .frame(minHeight: 100, maxHeight: 300)
                }
                .frame(minWidth: 200)
                .cornerRadius(4)
            }
            .padding()
            .cornerRadius(4)
            
            // BOTTOM SECTION
            VStack {
                Button("复制LaTeX") {
                    identifyProcess.copyLatexCode()
                }
                .padding()
                TextEditor(text: $identifyProcess.latexFormula)
                    .font(.system(size: 14, weight: .regular, design: .monospaced))
                    .frame(minHeight: 50, maxHeight: .infinity)
                    .scrollContentBackground(.hidden)
                    .scrollDisabled(true)
                    .padding()
                    .background(Color(.textBackgroundColor))
                    .cornerRadius(4)
            }
            .padding()
        }
        .frame(width:700)
        .padding()
        .onAppear {
            // 监听截图通知
            NotificationCenter.default.addObserver(
                forName: Notification.Name("TriggerScreenshot"),
                object: nil,
                queue: .main
            ) { _ in
                identifyProcess.startScreenshotProcess()
            }
            NotificationCenter.default.addObserver(
                forName: Notification.Name("TriggerCampusLogin"),
                object: nil,
                queue: .main
            ) { _ in
                identifyProcess.loginSCUNET()
            }
        }
    }
}

//#Preview {
//    MainBoardView()
//}
