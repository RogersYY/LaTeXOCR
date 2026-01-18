//
//  AppDelegate.swift
//  LaTeXOCR
//
//  Created by 颜家俊 on 2024/11/5.
//
import SwiftUI
import AppKit

class AppDelegate: NSObject, NSApplicationDelegate {
    var statusItem: NSStatusItem!
    var popover: NSPopover!
    var contentWindow: NSWindow?
    
    func applicationDidFinishLaunching(_ notification: Notification) {
              // 创建状态栏图标
              statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
              // if let button = statusItem.button {
              //     button.image = NSImage(systemSymbolName: "function", accessibilityDescription: "LaTeX OCR")
              //     button.action = #selector(togglePopover(_:))
              // }
              statusItem.button?.image=NSImage(systemSymbolName: "function", accessibilityDescription: "LaTeX OCR")
              // 状态栏功能列表
              setupMeauList()
        
              // 设置主窗口
              setupMainWindow()
        
              // 设置全局事件监听
              setupGlobalMonitor()
    }
    
    func setupMainWindow() {
        //        let contentView = ContentView()
        let contentView = MainBoardView()
        let hostingController = NSHostingController(rootView: contentView)
        
        contentWindow = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1000, height: 500),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        contentWindow?.center()
        contentWindow?.setFrameAutosaveName("Main Window")
        contentWindow?.contentViewController = hostingController
        contentWindow?.makeKeyAndOrderFront(nil)
        contentWindow?.isReleasedWhenClosed = false  // 重要：防止窗口关闭时被释放
        contentWindow?.minSize = NSSize(width: 700, height: 400)
    }
    
    func setupMeauList() {
        let menu = NSMenu()
        menu.addItem(NSMenuItem(title: "功能1",
                                action: #selector(function1(_:)),
                                keyEquivalent: ""))
        menu.addItem(NSMenuItem(title: "功能2",
                                action: #selector(function2(_:)),
                                keyEquivalent: ""))
        // 3. 添加分割线
        menu.addItem(NSMenuItem.separator())
        // 4. 带子菜单的菜单项
        let submenu = NSMenu()
        submenu.addItem(NSMenuItem(title: "子功能1",
                                   action: #selector(subFunction1(_:)),
                                   keyEquivalent: ""))
        submenu.addItem(NSMenuItem(title: "子功能2",
                                   action: #selector(subFunction2(_:)),
                                   keyEquivalent: ""))
        
        let subMenuItem = NSMenuItem(title: "更多功能",
                                     action: nil,
                                     keyEquivalent: "")
        subMenuItem.submenu = submenu
        menu.addItem(subMenuItem)
        
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "设置",
                                action: #selector(openSettings(_:)),
                                keyEquivalent: ","))
        
        // 5. 退出程序的菜单项
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "退出",
                                action: #selector(NSApplication.terminate(_:)),
                                keyEquivalent: "q"))
        
        // 将菜单设置给状态栏项
        statusItem.menu = menu
    }
    
    // 菜单项对应的动作方法
    @objc func function1(_ sender: Any?) {
        print("功能1被点击")
    }
    
    @objc func function2(_ sender: Any?) {
        print("功能2被点击")
    }
    
    @objc func subFunction1(_ sender: Any?) {
        print("子功能1被点击")
    }
    
    @objc func subFunction2(_ sender: Any?) {
        print("子功能2被点击")
    }
    
    @objc func openSettings(_ sender: Any?) {
        if #available(macOS 13.0, *) {
            NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: sender)
        } else {
            NSApp.sendAction(Selector(("showPreferencesWindow:")), to: nil, from: sender)
        }
    }
    
    @objc func togglePopover(_ sender: Any?) {
        if let contentWindow = contentWindow {
            if contentWindow.isVisible {
                contentWindow.orderOut(nil)
            } else {
                contentWindow.makeKeyAndOrderFront(nil)
            }
        }
    }
    
    private func setupGlobalMonitor() {
        let handler: (NSEvent) -> Void = { event in
            if event.modifierFlags.contains(.command) &&
                event.modifierFlags.contains(.shift) &&
                event.keyCode == 0 /* A key */ {
                // 触发截图
                NotificationCenter.default.post(name: Notification.Name("TriggerScreenshot"), object: nil)
            }
        }
        
        NSEvent.addGlobalMonitorForEvents(matching: .keyDown) { event in
            handler(event)
        }
        NSEvent.addLocalMonitorForEvents(matching: .keyDown) { event in
            handler(event)
            return event
        }
    }
    
    // 处理点击dock图标事件
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if !flag {
            contentWindow?.makeKeyAndOrderFront(nil)
        }
        return true
    }
}
