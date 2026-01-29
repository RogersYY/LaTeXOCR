//
//  SettingsView.swift
//  LaTeXOCR
//
//  Created by 颜家俊 on 2025/4/14.
//

import SwiftUI

struct SettingsView: View {
    @AppStorage("apiBaseURL") private var apiBaseURL: String = ""
    @AppStorage("apiKey") private var apiKey: String = ""
    @AppStorage("apiModel") private var apiModel: String = "gpt-5.2"
    @AppStorage("apiModelCustom") private var apiModelCustom: String = ""
    @AppStorage("copyFormat") private var copyFormat: String = "latex"
    @State private var showApiKey: Bool = false
    
    private let availableModels = [
        "gpt-5.2",
        "gpt-4.1-mini",
        "其他"
    ]
    
    var body: some View {
        Form {
            Section("OCR API") {
                TextField("API 地址", text: $apiBaseURL)
                    .textFieldStyle(.roundedBorder)
                HStack {
                    if showApiKey {
                        TextField("API Key", text: $apiKey)
                            .textFieldStyle(.roundedBorder)
                    } else {
                        SecureField("API Key", text: $apiKey)
                            .textFieldStyle(.roundedBorder)
                    }
                    Button {
                        showApiKey.toggle()
                    } label: {
                        Image(systemName: showApiKey ? "eye.slash" : "eye")
                    }
                    .buttonStyle(.borderless)
                    .help(showApiKey ? "隐藏 API Key" : "显示 API Key")
                }
                Picker("模型", selection: $apiModel) {
                    ForEach(availableModels, id: \.self) { model in
                        Text(model).tag(model)
                    }
                }
                .pickerStyle(.menu)
                if apiModel == "其他" {
                    TextField("模型名称", text: $apiModelCustom)
                        .textFieldStyle(.roundedBorder)
                }
                Picker("自动复制格式", selection: $copyFormat) {
                    Text("LaTeX").tag("latex")
                    Text("MathML(word)").tag("mathml")
                }
                .pickerStyle(.menu)
                Text("API地址请填写到 /v1 即可，例如: https://api.openai.com/v1")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(20)
        .frame(width: 420)
    }
}

#Preview {
    SettingsView()
}
