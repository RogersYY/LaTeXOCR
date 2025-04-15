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
    
    func makeNSView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        let webView = WKWebView(frame: .zero, configuration: config)
        // 设置透明背景
        webView.setValue(false, forKey: "drawsBackground")
        
        // 允许自动调整大小
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
                try {
                    katex.render("\(escapedFormula)", document.getElementById("formula"), {
                        displayMode: true,
                        throwOnError: false
                    });
                } catch (e) {
                    document.getElementById("formula").innerHTML = "公式错误: " + e.message;
                }
            </script>
        </body>
        </html>
        """
        
        webView.loadHTMLString(html, baseURL: nil)
    }
}
