//
//  MainBoardView.swift
//  LaTeXOCR
//
//  Created by 颜家俊 on 2025/4/14.
//

import SwiftUI
import WebKit

struct MainBoardView: View {
    //    @State private var image: NSImage? = nil
    //    @State private var latexFormula: String = ""
    //    @State private var savedImageURL: URL? // New state to store the URL of the saved image
    //    @State private var image_base64String: String = "" // 新增状态变量存储Base64编码字符串
    // 添加 IdentifyProcess 实例
    @StateObject private var identifyProcess = IdentifyProcess()
    @State private var mathMLRequestToken: Int = 0
    
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
                    
                    // KaTeXView(latexFormula: identifyProcess.latexFormula)
                    //     .frame(minHeight: 100, maxHeight: 300)
                    ZStack(alignment: .bottom) {
                        KaTeXView(latexFormula: identifyProcess.latexFormula, requestToken: mathMLRequestToken) { mathML in
                            identifyProcess.mathmlFormula = mathML
                            identifyProcess.completeMathMLCopyIfNeeded()
                        }
                        if identifyProcess.isLoading {
                            ProgressView("识别中...")
                                .padding(.bottom, 6)
                        }
                    }
                    .frame(minHeight: 100, maxHeight: 300)
                }
                .frame(minWidth: 200)
                .cornerRadius(4)
            }
            .padding()
            .cornerRadius(4)
            
            // BOTTOM SECTION
            VStack {
                HStack {
                    Button("复制LaTeX") {
                        identifyProcess.copyLatexWithFeedback()
                    }
                    Button("复制MathML(word)") {
                        if identifyProcess.latexFormula.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                            identifyProcess.showCopyFeedback("暂无公式可复制")
                            return
                        }
                        if identifyProcess.mathmlFormula.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                            identifyProcess.pendingMathMLCopy = true
                            identifyProcess.pendingCopyFeedback = true
                            identifyProcess.showCopyFeedback("生成 MathML...")
                            mathMLRequestToken += 1
                        } else {
                            let success = identifyProcess.copyFormulaCode(copyFormula: "mathml")
                            identifyProcess.showCopyFeedback(success ? "已复制 MathML(word)" : "复制失败")
                        }
                    }
                }
                // Button("复制LaTeX") {
                //     identifyProcess.copyLatexCode()
                // }
                .padding()
                Text(identifyProcess.copyFeedbackMessage.isEmpty ? " " : identifyProcess.copyFeedbackMessage)
                    .font(.footnote)
                    .foregroundStyle(.green)
                    .frame(height: 16)
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
        .frame(minWidth: 700, minHeight: 400)
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
        }
    }
}

#Preview {
    MainBoardView()
}
