import sys
import time
import threading

class Spinner:
    """
    一个简单的命令行旋转加载动画
    """
    def __init__(self, message="Thinking...", delay=0.1):
        # 类似 npm 的旋转字符
        self.spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.delay = delay
        self.message = message
        self.running = False
        self.thread = None
        self.lock = threading.Lock() # 保护 stdout 的锁
        self.last_print_time = 0     # 上次打印内容的时间
        self.visible = False         # 标记 Spinner 当前是否可见

    def _spin(self):
        """旋转逻辑"""
        i = 0
        while self.running:
            with self.lock:
                # 只有在距离上次打印内容超过一定时间后才显示 Spinner
                # 这样可以避免在快速输出内容时 Spinner 闪烁
                if time.time() - self.last_print_time > 0.1:
                    sys.stdout.write(f"\r{self.spinner[i % len(self.spinner)]} {self.message}\033[K")
                    sys.stdout.flush()
                    self.visible = True
            time.sleep(self.delay)
            i += 1

    def start(self, message=None):
        """开始旋转"""
        if self.running:
            if message:
                self.message = message
            return
        
        if message:
            self.message = message
            
        self.running = True
        self.thread = threading.Thread(target=self._spin)
        # 设置为守护线程，防止主程序退出时卡住
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        """停止旋转并清除行"""
        with self.lock:
            self.running = False
            self.visible = False # 标记不可见，防止后续写入
            # 清除最后一行显示
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()

        if self.thread:
            self.thread.join()
            self.thread = None

    def write(self, content, stream=None, color=None):
        """
        线程安全地写入内容，会自动处理 Spinner 的清除和重绘
        
        Args:
            content: 要写入的内容
            stream: 写入的目标流，默认为 sys.stdout
            color: ANSI 颜色代码（例如 "\033[90m"）
        """
        if stream is None:
            stream = sys.stdout
            
        with self.lock:
            # 如果已经停止运行，不再写入任何内容，防止僵尸线程污染输出
            if not self.running:
                return

            # 只有当 Spinner 可见时才清除
            if self.visible:
                sys.stdout.write("\r\033[K")
                sys.stdout.flush()
                self.visible = False
            
            # 写入实际内容
            if color:
                stream.write(color)
            
            stream.write(content)
            
            if color:
                stream.write("\033[0m")
                
            stream.flush()
            
            # 更新最后打印时间，推迟下一次 Spinner 的显示
            self.last_print_time = time.time()
