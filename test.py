import tkinter as tk
from tkinter import ttk, filedialog, colorchooser
import threading
import math
import json
import queue
from langchain.llms import Ollama
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from tkinter import PhotoImage
from PIL import Image, ImageTk
import copy

class MindMapNode:
    def __init__(self, x, y, settings, text="", parent=None):
        self.x = x
        self.y = y
        self.vx = 0  # 速度
        self.vy = 0
        self.target_x = x  # 目标位置
        self.target_y = y
        self.text = text
        self.parent = parent
        self.children = []
        self.depth = 0 if parent is None else parent.depth + 1
        # 根据深度调整节点大小
        self.width = settings["节点外观"]["根节点宽度"] if parent is None else max(
            settings["节点外观"]["子节点最小宽度"], 
            settings["节点外观"]["根节点宽度"] - self.depth * 10
        )
        self.height = settings["节点外观"]["根节点高度"] if parent is None else max(
            settings["节点外观"]["子节点最小高度"], 
            settings["节点外观"]["根节点高度"] - self.depth * 5
        )
        self.expanded = False # 是否展开子节点

    def to_dict(self):
        """将节点转换为字典格式以便序列化"""
        return {
            'x': self.x,
            'y': self.y,
            'text': self.text,
            'expanded': self.expanded,
            'children': [child.to_dict() for child in self.children]
        }

    @classmethod
    def from_dict(cls, data, parent=None):
        """从字典创建节点"""
        node = cls(data['x'], data['y'], data['text'], parent)
        node.expanded = data['expanded']
        for child_data in data['children']:
            child = cls.from_dict(child_data, node)
            node.children.append(child)
        return node

class MindMap:
    def __init__(self):
        self.settings = {
            # 物理引擎参数
            "物理引擎": {
                "弹簧系数": 0.05,  # spring_k
                "排斥力系数": 8000,  # repulsion
                "阻尼系数": 0.8,    # damping
                "目标距离": 250,    # target_dist
                "线之间排斥力": 1000, # line_repulsion
                "最大速度": 10.0,   # max_velocity
                "最小距离": 50.0,   # min_distance
            },
            # 节点外观
            "节点外观": {
                "文字初始大小": 14,  # word_size
                "节点距离系数": 1.2, # node_distance_rate
                "根节点宽度": 140,   # root_width
                "根节点高度": 50,    # root_height
                "子节点最小宽度": 100, # min_child_width
                "子节点最小高度": 40, # min_child_height
                "节点圆角半径": 10,  # node_radius
                "节点阴影": True,   # node_shadow
                "连接线粗细": 2,    # line_width
                "连接线颜色": "#666666", # line_color
                "连接线样式": "曲线", # line_style: 直线/曲线/折线
            },
            # 自动生成参数
            "自动生成": {
                "生成间隔(毫秒)": 5000,  # auto_gen_interval
                "单次生成数量": 8,      # gen_num
                "包含父节点路径": True,   # include_parent_path
                "最大生成深度": 5,      # max_depth
                "智能排序": True,      # smart_sort
            },
            # 布局参数
            "布局": {
                "最小缩放比例": 0.2,     # min_scale
                "最大缩放比例": 5.0,     # max_scale
                "子节点角度范围": 120,   # child_angle_range
                "自动居中": True,      # auto_center
                "动画速度": 1.0,      # animation_speed
                "网格显示": False,    # show_grid
                "网格大小": 50,      # grid_size
            },
            # 主题配色
            "主题配色": {
                "背景色": "#FFFFFF",    # background_color
                "根节点": "#E3F2FD",    # root_color
                "一级节点": "#BBDEFB",  # level1_color
                "二级节点": "#90CAF9",  # level2_color
                "三级节点": "#64B5F6",  # level3_color
                "选中节点": "#81D4FA",  # selected_color
                "文字颜色": "#333333",  # text_color
                "按钮颜色": "#2196F3",  # button_color
            }
        }
        self.root = tk.Tk()
        self.root.title("思维导图生成器")
        self.root.geometry("1200x800")
        
        # 设置主题样式
        style = ttk.Style()
        style.theme_use('clam')
        
        # 自定义颜色和样式
        style.configure("TButton",
            padding=8,
            relief="flat",
            background=self.settings["主题配色"]["按钮颜色"],
            foreground="white",
            font=("Microsoft YaHei", 10, "bold"),
            borderwidth=0
        )
        
        style.map("TButton",
            background=[('active', '#1976D2'), ('pressed', '#0D47A1')],
            foreground=[('active', 'white'), ('pressed', 'white')]
        )
        
        style.configure("TEntry",
            padding=8,
            relief="flat",
            font=("Microsoft YaHei", 10),
            fieldbackground="#F5F5F5",
            borderwidth=1
        )
        
        style.configure("Toolbar.TFrame",
            background=self.settings["主题配色"]["背景色"],
            relief="raised",
            borderwidth=1
        )
        
        # 加载图标资源
        try:
            self.start_icon = PhotoImage(file="assets/start.png").subsample(2,2)
            self.add_icon = PhotoImage(file="assets/add.png").subsample(2,2)
            self.settings_icon = PhotoImage(file="assets/settings.png").subsample(2,2)
            self.new_icon = PhotoImage(file="assets/new.png").subsample(2,2)
            self.import_icon = PhotoImage(file="assets/import.png").subsample(2,2) 
            self.export_icon = PhotoImage(file="assets/export.png").subsample(2,2)
            self.copy_icon = PhotoImage(file="assets/copy.png").subsample(2,2)
            self.paste_icon = PhotoImage(file="assets/paste.png").subsample(2,2)
            self.undo_icon = PhotoImage(file="assets/undo.png").subsample(2,2)
            self.redo_icon = PhotoImage(file="assets/redo.png").subsample(2,2)
        except:
            self.start_icon = None
            self.add_icon = None
            self.settings_icon = None
            self.new_icon = None
            self.import_icon = None
            self.export_icon = None
            self.copy_icon = None
            self.paste_icon = None
            self.undo_icon = None
            self.redo_icon = None
        
        # 初始化Ollama LLM
        callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
        self.llm = Ollama(
            model="llama3.1:8b",
            callback_manager=callback_manager
        )
        
        # 用于线程间通信的队列
        self.llm_queue = queue.Queue()
        self.result_queue = queue.Queue()
        
        # 启动LLM处理线程
        self.llm_thread = threading.Thread(target=self.llm_worker, daemon=True)
        self.llm_thread.start()
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)
        
        # 工具栏
        self.toolbar = ttk.Frame(self.main_frame, style="Toolbar.TFrame")
        self.toolbar.pack(side="top", fill="x", padx=10, pady=5)

        # 文件操作按钮
        self.file_frame = ttk.Frame(self.toolbar)
        self.file_frame.pack(side="left", padx=5)
        
        ttk.Button(self.file_frame, text="新建", image=self.new_icon, compound="left", command=self.new_map).pack(side="left", padx=2)
        ttk.Button(self.file_frame, text="导入", image=self.import_icon, compound="left", command=self.import_map).pack(side="left", padx=2)
        ttk.Button(self.file_frame, text="导出", image=self.export_icon, compound="left", command=self.export_map).pack(side="left", padx=2)
        
        # 编辑操作按钮
        self.edit_frame = ttk.Frame(self.toolbar)
        self.edit_frame.pack(side="left", padx=5)
        
        ttk.Button(self.edit_frame, text="复制", image=self.copy_icon, compound="left", command=self.copy_node).pack(side="left", padx=2)
        ttk.Button(self.edit_frame, text="粘贴", image=self.paste_icon, compound="left", command=self.paste_node).pack(side="left", padx=2)
        ttk.Button(self.edit_frame, text="撤销", image=self.undo_icon, compound="left", command=self.undo).pack(side="left", padx=2)
        ttk.Button(self.edit_frame, text="重做", image=self.redo_icon, compound="left", command=self.redo).pack(side="left", padx=2)
        
        # 原有按钮
        self.start_btn = ttk.Button(self.toolbar, 
            text="开始自动生成",
            command=self.toggle_auto_generate,
            image=self.start_icon if self.start_icon else None,
            compound="left"
        )
        self.start_btn.pack(side="left", padx=5)
        
        self.add_btn = ttk.Button(self.toolbar,
            text="新建子节点",
            command=self.add_child_node,
            image=self.add_icon if self.add_icon else None,
            compound="left"
        )
        self.add_btn.pack(side="left", padx=5)
        
        self.settings_btn = ttk.Button(self.toolbar,
            text="设置",
            command=self.show_settings,
            image=self.settings_icon if self.settings_icon else None,
            compound="left"
        )
        self.settings_btn.pack(side="left", padx=5)
        
        # 画布容器
        self.canvas_frame = ttk.Frame(self.main_frame)
        self.canvas_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 画布
        self.canvas = tk.Canvas(
            self.canvas_frame,
            width=1200,
            height=800,
            bg=self.settings["主题配色"]["背景色"],
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)
        
        # 滚动条
        self.h_scrollbar = ttk.Scrollbar(self.canvas_frame, orient="horizontal", command=self.canvas.xview)
        self.v_scrollbar = ttk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.h_scrollbar.set, yscrollcommand=self.v_scrollbar.set)
        
        self.h_scrollbar.pack(side="bottom", fill="x")
        self.v_scrollbar.pack(side="right", fill="y")
        
        # 缩放和平移相关变量
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        # 节点数据
        self.root_node = MindMapNode(600, 400, self.settings, "中心主题")
        self.root_node.expanded = True # 根节点默认展开
        self.selected_node = None
        self.dragging = False
        self.auto_generating = False
        self.auto_gen_thread = None
        
        # 复制粘贴相关
        self.clipboard = None
        
        # 撤销重做相关
        self.history = []
        self.future = []
        self.save_state()
        
        # 绑定事件
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.root.bind("<Delete>", self.delete_selected_node)
        self.root.bind("<Control-c>", lambda e: self.copy_node())
        self.root.bind("<Control-v>", lambda e: self.paste_node())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        
        # 启动物理模拟和绘制循环
        self.update_physics()
        self.draw()
        
        # 启动结果处理循环
        self.process_results()

    def get_node_angle_range(self, node):
        """计算节点的当前角度范围"""
        if not node.parent:
            return (-2*math.pi, 2*math.pi)
            
        # 如果父节点是根节点,则无限制
        if node.parent.parent is None:
            return (-2*math.pi, 2*math.pi)
            
        # 计算父节点相对于其父节点的角度
        dx = node.parent.x - node.parent.parent.x 
        dy = node.parent.y - node.parent.parent.y
        parent_angle = math.atan2(dy, dx)
            
        # 基于父节点角度,限制在设定范围内
        half_range = math.pi * self.settings["布局"]["子节点角度范围"]/360
        min_angle = (parent_angle - half_range)
        max_angle = (parent_angle + half_range)
        
        return (min_angle, max_angle)
    def save_state(self):
        """保存当前状态到历史记录"""
        state = self.root_node.to_dict()
        self.history.append(state)
        self.future.clear()  # 清空重做历史
        if len(self.history) > 50:  # 限制历史记录数量
            self.history.pop(0)
    def show_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("设置")
        settings_window.geometry("600x800")
        
        style = ttk.Style()
        style.configure("Settings.TNotebook", 
            background=self.settings["主题配色"]["背景色"],
            borderwidth=0
        )
        style.configure("Settings.TFrame",
            background=self.settings["主题配色"]["背景色"]
        )
        
        notebook = ttk.Notebook(settings_window, style="Settings.TNotebook")
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        entries = {}
        
        # 为每个分类创建一个标签页
        for category, settings in self.settings.items():
            frame = ttk.Frame(notebook, style="Settings.TFrame")
            notebook.add(frame, text=category)
            
            canvas = tk.Canvas(frame, background=self.settings["主题配色"]["背景色"])
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas, style="Settings.TFrame")
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            entries[category] = {}
            row = 0
            for key, value in settings.items():
                label_frame = ttk.Frame(scrollable_frame, style="Settings.TFrame")
                label_frame.grid(row=row, column=0, sticky="w", padx=10, pady=5)
                
                ttk.Label(label_frame, text=key, 
                    font=("Microsoft YaHei", 10),
                    background=self.settings["主题配色"]["背景色"]
                ).pack(side="left")
                
                if isinstance(value, bool):
                    var = tk.BooleanVar(value=value)
                    check = ttk.Checkbutton(label_frame, variable=var)
                    check.pack(side="right")
                    entries[category][key] = var
                elif isinstance(value, str):
                    if "颜色" in key:
                        color_btn = tk.Button(label_frame, 
                            width=8, 
                            bg=value,
                            command=lambda k=key, c=category: self.choose_color(k, c, entries)
                        )
                        color_btn.pack(side="right")
                        entries[category][key] = color_btn
                    else:
                        entry = ttk.Entry(label_frame, width=20)
                        entry.insert(0, str(value))
                        entry.pack(side="right")
                        entries[category][key] = entry
                else:
                    entry = ttk.Entry(label_frame, width=20)
                    entry.insert(0, str(value))
                    entry.pack(side="right")
                    entries[category][key] = entry
                
                row += 1
                
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
        def save_settings():
            for category, category_entries in entries.items():
                for key, entry in category_entries.items():
                    try:
                        if isinstance(entry, tk.BooleanVar):
                            self.settings[category][key] = entry.get()
                        elif isinstance(entry, tk.Button):  # 颜色按钮
                            self.settings[category][key] = entry.cget("bg")
                        else:
                            # 对特定设置使用整数转换
                            if "间隔" in key or "数量" in key or "大小" in key:
                                self.settings[category][key] = int(float(entry.get()))
                            else:
                                self.settings[category][key] = float(entry.get())
                    except ValueError:
                        pass
            settings_window.destroy()
                
        ttk.Button(settings_window, text="确定", 
                  command=save_settings).pack(pady=10)
        
    def choose_color(self, key, category, entries):
        """颜色选择器"""
        color = tk.colorchooser.askcolor(
            color=self.settings[category][key],
            title="选择颜色"
        )
        if color[1]:
            entries[category][key].configure(bg=color[1])
            
    def update_physics(self):
        """更新节点位置的物理模拟"""
        def update_node_recursive(node):
            # 中心节点不受力
            if node.parent == None or node.parent.expanded == False:
                node.vx = 0
                node.vy = 0
                for child in node.children:
                    update_node_recursive(child)
                return
                
            # 计算所有节点间的排斥力
            for other in self.get_all_nodes():
                if other != node and other.parent and other.parent.expanded:
                    dx = node.x - other.x
                    dy = node.y - other.y
                    dist = math.sqrt(dx*dx + dy*dy)
                    if dist < self.settings["物理引擎"]["最小距离"]:
                        dist = self.settings["物理引擎"]["最小距离"]
                    force = self.settings["物理引擎"]["排斥力系数"] / (dist * dist)
                    node.vx += force * dx / dist
                    node.vy += force * dy / dist
            
            # 计算线之间的排斥力
            for other_node in self.get_all_nodes():
                if (other_node.parent and node.parent and other_node != node 
                    and other_node.parent.expanded and node.parent.expanded):
                    line1_mid_x = (node.x + node.parent.x) / 2
                    line1_mid_y = (node.y + node.parent.y) / 2
                    line2_mid_x = (other_node.x + other_node.parent.x) / 2
                    line2_mid_y = (other_node.y + other_node.parent.y) / 2
                    
                    dx = line1_mid_x - line2_mid_x
                    dy = line1_mid_y - line2_mid_y
                    dist = math.sqrt(dx*dx + dy*dy)
                    if dist < self.settings["物理引擎"]["最小距离"]:
                        dist = self.settings["物理引擎"]["最小距离"]
                    
                    force = self.settings["物理引擎"]["线之间排斥力"] / (dist * dist)
                    node.vx += force * dx / dist
                    node.vy += force * dy / dist
            
            # 计算弹簧力
            if node.parent:
                dx = node.x - node.parent.x
                dy = node.y - node.parent.y
                dist = math.sqrt(dx*dx + dy*dy)
                # 根据深度增加目标距离
                target_dist = self.settings["物理引擎"]["目标距离"] * (1 + node.depth * 0.5)
                force = self.settings["物理引擎"]["弹簧系数"] * (dist - target_dist)
                node.vx -= force * dx / dist
                node.vy -= force * dy / dist
                
                # 限制节点在其角度范围内
                angle_range = self.get_node_angle_range(node)
                if angle_range:
                    start_angle, end_angle = angle_range
                    current_angle = math.atan2(dy, dx)

                    if current_angle < start_angle:
                        current_angle = start_angle
                    elif current_angle > end_angle:
                        current_angle = end_angle
                    
                    # 根据角度计算新位置
                    node.x = node.parent.x + dist * math.cos(current_angle)
                    node.y = node.parent.y + dist * math.sin(current_angle)
                    
            # 限制最大速度
            speed = math.sqrt(node.vx * node.vx + node.vy * node.vy)
            if speed > self.settings["物理引擎"]["最大速度"]:
                node.vx *= self.settings["物理引擎"]["最大速度"] / speed
                node.vy *= self.settings["物理引擎"]["最大速度"] / speed
                
            # 更新速度和位置
            node.vx *= self.settings["物理引擎"]["阻尼系数"]
            node.vy *= self.settings["物理引擎"]["阻尼系数"]
            node.x += node.vx
            node.y += node.vy
            
            if node.expanded:
                for child in node.children:
                    update_node_recursive(child)
                
        update_node_recursive(self.root_node)
        self.root.after(16, self.update_physics)
        
    def get_all_nodes(self):
        """获取所有节点的列表"""
        nodes = []
        def collect_nodes(node):
            nodes.append(node)
            if node.expanded:
                for child in node.children:
                    collect_nodes(child)
        collect_nodes(self.root_node)
        return nodes
        
    def add_child_node(self):
        """添加新的子节点"""
        if self.selected_node:
            text = "新主题"
            self.create_child_node(self.selected_node, text)
            
    def get_node_path(self, node):
        """获取从根节点到当前节点的路径"""
        path = []
        current = node
        while current:
            path.insert(0, current.text)
            current = current.parent
        return " > ".join(path)
            
    def llm_worker(self):
        """LLM处理线程的工作函数"""
        while True:
            try:
                node, prompt = self.llm_queue.get()
                if node is None:  # 退出信号
                    break
                try:
                    # 如果设置了包含父节点路径，则在prompt中添加路径信息
                    if self.settings["自动生成"]["包含父节点路径"]:
                        path = self.get_node_path(node)
                        prompt = f"在思维导图路径'{path}'下，{prompt}"
                        
                    result = self.llm(prompt).strip()
                    topics = result.split('\n')
                    self.result_queue.put((node, topics))
                except Exception as e:
                    print(f"LLM错误: {e}")
                    self.result_queue.put((node, ["新主题"]))
            except queue.Empty:
                continue
                
    def process_results(self):
        """处理LLM结果的循环"""
        try:
            while not self.result_queue.empty():
                node, topics = self.result_queue.get_nowait()
                gen_num = int(self.settings["自动生成"]["单次生成数量"])
                for topic in topics[:gen_num]:
                    if topic.strip():  # 忽略空字符串
                        self.create_child_node(node, topic.strip())
        finally:
            self.root.after(100, self.process_results)
            
    def create_child_node(self, parent_node, text):
        """创建新的子节点"""
        # 计算新节点的位置
        if parent_node.children:
            # 获取最后一个子节点的角度
            last_child = parent_node.children[-1]
            dx = last_child.x - parent_node.x
            dy = last_child.y - parent_node.y
            last_angle = math.atan2(dy, dx)
            if last_angle < 0:
                last_angle += 2*math.pi
                
            # 根据父节点的深度确定限制角度范围
            if parent_node == self.root_node:
                # 根节点的子节点可以在360度范围内分布
                min_angle = 0
                max_angle = 2*math.pi
            else:
                # 非根节点的子节点在120度范围内分布
                parent_dx = parent_node.x - parent_node.parent.x
                parent_dy = parent_node.y - parent_node.parent.y
                parent_angle = math.atan2(parent_dy, parent_dx)
                if parent_angle < 0:
                    parent_angle += 2*math.pi
                    
                min_angle = parent_angle - math.pi/3  # 父节点角度减60度
                max_angle = parent_angle + math.pi/3  # 父节点角度加60度
                
            # 计算新节点的角度，确保在限制范围内
            angle = last_angle + math.pi/6  # 在最后一个子节点基础上增加30度
            angle = max(min_angle, min(max_angle, angle))  # 限制在允许范围内
        else:
            # 第一个子节点
            if parent_node == self.root_node:
                angle = 0  # 根节点的第一个子节点向右
            else:
                # 非根节点的第一个子节点沿父节点方向
                parent_dx = parent_node.x - parent_node.parent.x
                parent_dy = parent_node.y - parent_node.parent.y
                angle = math.atan2(parent_dy, parent_dx)
            
        # 根据深度增加距离
        distance = self.settings["物理引擎"]["目标距离"] * (1 + parent_node.depth * 0.5)
        
        new_x = parent_node.x + distance * math.cos(angle)
        new_y = parent_node.y + distance * math.sin(angle)
        
        new_node = MindMapNode(new_x, new_y, self.settings, text, parent_node)
        parent_node.children.append(new_node)
        parent_node.expanded = True  # 添加子节点时自动展开父节点
            
    def delete_selected_node(self, event=None):
        """删除选中的节点及其子节点"""
        if self.selected_node and self.selected_node != self.root_node:
            if self.selected_node.parent:
                self.selected_node.parent.children.remove(self.selected_node)
            self.selected_node = None
            
    def toggle_auto_generate(self):
        self.auto_generating = not self.auto_generating
        if self.auto_generating:
            self.start_btn.config(text="停止自动生成")
            self.auto_gen_thread = threading.Thread(target=self.auto_generate_loop, daemon=True)
            self.auto_gen_thread.start()
        else:
            self.start_btn.config(text="开始自动生成")
            
    def auto_generate_loop(self):
        while self.auto_generating:
            if self.selected_node:
                prompt = f"基于'{self.selected_node.text}'生成{self.settings['自动生成']['单次生成数量']}个相关的子主题，每个主题一行，用换行符分隔，请直接给出主题名称，不要有任何多余文字，不要带序号"
                self.llm_queue.put((self.selected_node, prompt))
            threading.Event().wait(self.settings["自动生成"]["生成间隔(毫秒)"] / 1000)
            
    def draw(self):
        self.canvas.delete("all")
        
        # 绘制网格（如果启用）
        if self.settings["布局"]["网格显示"]:
            grid_size = self.settings["布局"]["网格大小"] * self.scale
            # 绘制垂直线
            for x in range(0, int(self.canvas.winfo_width()), int(grid_size)):
                self.canvas.create_line(x, 0, x, self.canvas.winfo_height(), fill="#EEEEEE")
            # 绘制水平线
            for y in range(0, int(self.canvas.winfo_height()), int(grid_size)):
                self.canvas.create_line(0, y, self.canvas.winfo_width(), y, fill="#EEEEEE")

        def draw_node_recursive(node):
            if not node.parent or node.parent.expanded:
                # 绘制连接线
                if node.parent:
                    line_style = self.settings["节点外观"]["连接线样式"]
                    line_width = self.settings["节点外观"]["连接线粗细"]
                    line_color = self.settings["节点外观"]["连接线颜色"]
                    
                    if line_style == "直线":
                        self.canvas.create_line(
                            self.transform_x(node.parent.x),
                            self.transform_y(node.parent.y),
                            self.transform_x(node.x),
                            self.transform_y(node.y),
                            fill=line_color,
                            width=line_width
                        )
                    elif line_style == "曲线":
                        cx = (node.x + node.parent.x) / 2
                        cy = (node.y + node.parent.y) / 2
                        self.canvas.create_line(
                            self.transform_x(node.parent.x),
                            self.transform_y(node.parent.y),
                            self.transform_x(cx),
                            self.transform_y(cy),
                            self.transform_x(node.x),
                            self.transform_y(node.y),
                            fill=line_color,
                            width=line_width,
                            smooth=True
                        )
                    elif line_style == "折线":
                        mid_x = (node.x + node.parent.x) / 2
                        self.canvas.create_line(
                            self.transform_x(node.parent.x),
                            self.transform_y(node.parent.y),
                            self.transform_x(mid_x),
                            self.transform_y(node.parent.y),
                            self.transform_x(mid_x),
                            self.transform_y(node.y),
                            self.transform_x(node.x),
                            self.transform_y(node.y),
                            fill=line_color,
                            width=line_width
                        )

                # 绘制节点
                x1 = self.transform_x(node.x - node.width/2)
                y1 = self.transform_y(node.y - node.height/2)
                x2 = self.transform_x(node.x + node.width/2)
                y2 = self.transform_y(node.y + node.height/2)
                
                # 使用主题配色
                if node == self.root_node:
                    fill_color = self.settings["主题配色"]["根节点"]
                else:
                    depth_colors = [
                        self.settings["主题配色"]["一级节点"],
                        self.settings["主题配色"]["二级节点"],
                        self.settings["主题配色"]["三级节点"]
                    ]
                    fill_color = depth_colors[min(node.depth - 1, len(depth_colors) - 1)]

                if node == self.selected_node:
                    fill_color = self.settings["主题配色"]["选中节点"]

                # 绘制节点（带阴影）
                radius = self.settings["节点外观"]["节点圆角半径"] * self.scale
                if self.settings["节点外观"]["节点阴影"]:
                    # 绘制阴影
                    shadow_offset = 4 * self.scale
                    self.canvas.create_rectangle(
                        x1 + shadow_offset, y1 + shadow_offset,
                        x2 + shadow_offset, y2 + shadow_offset,
                        fill="#CCCCCC", width=0
                    )

                # 绘制圆角矩形
                self.canvas.create_rectangle(
                    x1+radius, y1, x2-radius, y2,
                    fill=fill_color, width=0
                )
                self.canvas.create_rectangle(
                    x1, y1+radius, x2, y2-radius,
                    fill=fill_color, width=0
                )
                self.canvas.create_arc(
                    x1, y1, x1+2*radius, y1+2*radius,
                    start=90, extent=90, fill=fill_color, width=0
                )
                self.canvas.create_arc(
                    x2-2*radius, y1, x2, y1+2*radius,
                    start=0, extent=90, fill=fill_color, width=0
                )
                self.canvas.create_arc(
                    x1, y2-2*radius, x1+2*radius, y2,
                    start=180, extent=90, fill=fill_color, width=0
                )
                self.canvas.create_arc(
                    x2-2*radius, y2-2*radius, x2, y2,
                    start=270, extent=90, fill=fill_color, width=0
                )
                
                # 设置文字大小和颜色
                font_size = int(self.settings["节点外观"]["文字初始大小"] * self.scale * 
                              (1 - node.depth * 0.1))
                font_size = max(8, font_size)
                
                self.canvas.create_text(
                    self.transform_x(node.x),
                    self.transform_y(node.y),
                    text=node.text,
                    width=node.width * self.scale * 0.9,
                    font=("Microsoft YaHei", font_size),
                    fill=self.settings["主题配色"]["文字颜色"]
                )
                
                # 如果有子节点，显示展开/收起按钮
                if node.children:
                    button_x = x2 - 15 * self.scale
                    button_y = self.transform_y(node.y)
                    button_size = 12 * self.scale
                    
                    # 绘制圆形按钮背景
                    self.canvas.create_oval(
                        button_x - button_size/2,
                        button_y - button_size/2,
                        button_x + button_size/2,
                        button_y + button_size/2,
                        fill="#FFFFFF",
                        outline="#666666"
                    )
                    
                    # 绘制+/-符号
                    self.canvas.create_text(
                        button_x,
                        button_y,
                        text="+" if not node.expanded else "-",
                        font=("Microsoft YaHei", int(10 * self.scale)),
                        fill="#666666"
                    )
                
                if node.expanded:
                    for child in node.children:
                        draw_node_recursive(child)
        
        draw_node_recursive(self.root_node)
        self.root.after(16, self.draw)
    def transform_x(self, x):
        return (x + self.offset_x) * self.scale
        
    def transform_y(self, y):
        return (y + self.offset_y) * self.scale
        
    def inverse_transform_x(self, x):
        return x / self.scale - self.offset_x
        
    def inverse_transform_y(self, y):
        return y / self.scale - self.offset_y
        
    def find_node_at(self, x, y):
        def check_node(node):
            if not node.parent or node.parent.expanded:
                tx = self.transform_x(node.x)
                ty = self.transform_y(node.y)
                
                # 检查是否点击了展开/收起按钮
                if node.children:
                    button_x = tx + node.width/2 * self.scale - 15 * self.scale
                    button_y = ty
                    button_size = 12 * self.scale
                    
                    if (button_x - button_size/2 <= x <= button_x + button_size/2 and
                        button_y - button_size/2 <= y <= button_y + button_size/2):
                        node.expanded = not node.expanded
                        return None
                
                if (tx - node.width/2 * self.scale <= x <= tx + node.width/2 * self.scale and
                    ty - node.height/2 * self.scale <= y <= ty + node.height/2 * self.scale):
                    return node
                    
                if node.expanded:
                    for child in node.children:
                        result = check_node(child)
                        if result:
                            return result
            return None
            
        return check_node(self.root_node)
        
    def on_click(self, event):
        node = self.find_node_at(event.x, event.y)
        if node:
            self.selected_node = node
            self.dragging = True
            self.drag_start_x = event.x
            self.drag_start_y = event.y
        else:
            self.selected_node = None
            self.dragging = True
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            
    def on_drag(self, event):
        if self.dragging:
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y
            
            if self.selected_node:
                self.selected_node.x += dx / self.scale
                self.selected_node.y += dy / self.scale
            else:
                self.offset_x += dx / self.scale
                self.offset_y += dy / self.scale
                
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            
    def on_release(self, event):
        self.dragging = False
        
    def on_right_click(self, event):
        node = self.find_node_at(event.x, event.y)
        if node:
            prompt = f"基于'{node.text}'生成{self.settings['自动生成']['单次生成数量']}个相关的子主题，每个主题一行，用换行符分隔，请直接给出主题名称，不要有任何多余文字，不要带序号"
            self.llm_queue.put((node, prompt))
            
    def on_double_click(self, event):
        node = self.find_node_at(event.x, event.y)
        if node:
            dialog = tk.Toplevel(self.root)
            dialog.title("编辑节点")
            
            entry = ttk.Entry(dialog)
            entry.insert(0, node.text)
            entry.pack(padx=20, pady=20)
            
            def save():
                node.text = entry.get()
                dialog.destroy()
                
            ttk.Button(dialog, text="确定", command=save).pack(pady=10)
            
    def on_mousewheel(self, event):
        # Windows下的滚轮事件
        delta = event.delta / 120.0
        
        # 获取鼠标在画布上的坐标
        mouse_x = event.x
        mouse_y = event.y
        
        # 获取鼠标在世界坐标系中的位置
        world_x = self.inverse_transform_x(mouse_x)
        world_y = self.inverse_transform_y(mouse_y)
        
        # 更新缩放比例
        old_scale = self.scale
        self.scale *= (1.1 ** delta)
        self.scale = max(0.1, min(5.0, self.scale))  # 限制缩放范围
        
        # 计算缩放后鼠标位置对应的世界坐标
        new_world_x = self.inverse_transform_x(mouse_x)
        new_world_y = self.inverse_transform_y(mouse_y)
        
        # 调整偏移量，使鼠标位置保持不变
        self.offset_x += (new_world_x - world_x)
        self.offset_y += (new_world_y - world_y)
    def undo(self):
        """撤销操作"""
        if len(self.history) > 1:
            self.future.append(self.history.pop())
            state = self.history[-1]
            self.root_node = MindMapNode.from_dict(copy.deepcopy(state))

    def redo(self):
        """重做操作"""
        if self.future:
            state = self.future.pop()
            self.history.append(state)
            self.root_node = MindMapNode.from_dict(copy.deepcopy(state))

    def new_map(self):
        """新建思维导图"""
        self.root_node = MindMapNode(600, 400, self.settings, "中心主题")
        self.root_node.expanded = True
        self.selected_node = None
        self.save_state()

    def export_map(self):
        """导出思维导图到文件"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            data = self.root_node.to_dict()
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def import_map(self):
        """从文件导入思维导图"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.root_node = MindMapNode.from_dict(data)
                self.selected_node = None
                self.save_state()
            except Exception as e:
                tk.messagebox.showerror("错误", f"导入失败: {str(e)}")

    def copy_node(self):
        """复制选中的节点"""
        if self.selected_node and self.selected_node != self.root_node:
            self.clipboard = self.selected_node.to_dict()

    def paste_node(self):
        """粘贴节点"""
        if self.clipboard and self.selected_node:
            new_node = MindMapNode.from_dict(self.clipboard, self.selected_node)
            self.selected_node.children.append(new_node)
            self.selected_node.expanded = True
            self.save_state()

if __name__ == "__main__":
    mind_map = MindMap()
    mind_map.root.mainloop()