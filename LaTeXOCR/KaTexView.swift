//
//  KaTexView.swift
//  LaTeXOCR
//
//  Created by 颜家俊 on 2025/4/14.
//

import WebKit
import SwiftUI

// KaTeX 视图实现
struct KaTeXView: NSViewRepresentable {
    var latexFormula: String
    var onMathMLReceived: ((String) -> Void)? // 添加回调属性
    
    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }
    
    class Coordinator: NSObject, WKScriptMessageHandler {
        var parent: KaTeXView
        
        init(_ parent: KaTeXView) {
            self.parent = parent
        }
        
        func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
            if message.name == "mathMLHandler", let mathML = message.body as? String {
                parent.onMathMLReceived?(mathML)
            }
        }
    }
    
    func makeNSView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        let userContentController = WKUserContentController()
        userContentController.add(context.coordinator, name: "mathMLHandler")
        config.userContentController = userContentController
        
        let webView = WKWebView(frame: .zero, configuration: config)
        webView.setValue(false, forKey: "drawsBackground")
        
        webView.autoresizingMask = [.width, .height]
        webView.translatesAutoresizingMaskIntoConstraints = true
        
        return webView
    }
    
    func updateNSView(_ webView: WKWebView, context: Context) {
        let escapedFormula = latexFormula.replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "\"", with: "\\\"")
        
        let html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.4/dist/katex.min.css">
            <script src="https://cdn.jsdelivr.net/npm/katex@0.16.4/dist/katex.min.js"></script>
            <style>
                html, body {
                    margin: 0;
                    padding: 0;
                    width: 100%;
                    height: 100%;
                    background: transparent;
                    overflow: auto;
                }
                #formula {
                    width: 100%;
                    padding: 10px;
                    box-sizing: border-box;
                    text-align: center;
                }
                .katex-display {
                    margin: 0;
                    display: flex;
                    justify-content: center;
                }
            </style>
        </head>
        <body>
            <div id="formula"></div>
            <script>
                    function extractPureMathML(htmlString) {
                        try {
                            // 修改正则表达式，增加适当的转义
                            const mathmlRegex = /<math[^>]*>([\\s\\S]*?)<\\/math>/;
                            const mathMatch = htmlString.match(mathmlRegex);
        
                            if (!mathMatch || !mathMatch[0]) {
                                console.error('未找到math标签');
                                return null;
                            }
        
                            // 获取完整的 math 标签内容
                            let mathmlString = mathMatch[0];
        
                            // 移除 semantics 和 annotation 标签
                            const semanticsStartIndex = mathmlString.indexOf('<semantics>');
                            if (semanticsStartIndex !== -1) {
                                // 提取 semantics 标签之前的内容
                                const beforeSemantics = mathmlString.substring(0, semanticsStartIndex);
        
                                // 修改这个正则表达式的转义
                                const mrowRegex = /<semantics>([\\s\\S]*?)<annotation/;
                                const mrowMatch = mathmlString.match(mrowRegex);
        
                                if (mrowMatch && mrowMatch[1]) {
                                    const mainContent = mrowMatch[1];
                                    const mathEndTag = '</math>';
                                    return beforeSemantics + mainContent + mathEndTag;
                                }
                            }
        
                            return mathmlString;
                        } catch (error) {
                            console.error('MathML提取错误:', error);
                            return null;
                        }
                    }
                try {
                    katex.render("\(escapedFormula)", document.getElementById("formula"), {
                        displayMode: true,
                        throwOnError: false
                    });
                    var mathmlcode = katex.renderToString("\(escapedFormula)", {
                        output: "mathml",
                        throwOnError: false
                    });
                    let pureMathML = extractPureMathML(mathmlcode);
                    window.webkit.messageHandlers.mathMLHandler.postMessage(pureMathML);
                } catch (e) {
                    document.getElementById("formula").innerHTML = "公式错误: " + e.message;
                    window.webkit.messageHandlers.mathMLHandler.postMessage(null);
                }
            </script>
        </body>
        </html>
        """
        
        webView.loadHTMLString(html, baseURL: nil)
    }
}
