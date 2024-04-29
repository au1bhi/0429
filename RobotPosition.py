import matplotlib # type: ignore
from tkinter import *
from matplotlib.figure import Figure# type: ignore
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg # type: ignore


def run():
    def drawPic():
        from Demo import RobotAPI # type: ignore
        api = RobotAPI('avatar123', '8.130.175.216', '39092')
        # api = RobotAPI('avatar123', '192.168.11.1', '1448')
        # 清空图像，以使得前后两次绘制的图像不会重叠
        drawPic.f.clf()
        drawPic.a = drawPic.f.add_subplot(111)

        # ================================================
        all_points = []
        for e in api.get_points():
            _ = e['pose']
            all_points.append((_['x'], _['y'], e['id']))
        for p in all_points:
            x, y, _id = p
            drawPic.a.scatter(x, y, c='r', s=100)
            drawPic.a.annotate(_id, (x + 0.1, y + 0.1))

        # ================================================
        _ = api.get_pose()
        try:
            x, y = _['x'], _['y']
        except Exception as ex:
            print('---------------->>>', _, ex)
            return None
        drawPic.a.scatter(x, y, c='g', s=100)
        drawPic.a.annotate('Robot', (x + 0.1, y + 0.1))
        # ================================================

        drawPic.a.set_title('robot position')
        drawPic.canvas.draw()
        root.after(300, drawPic)

    matplotlib.use('TkAgg')
    root = Tk()
    # 在Tk的GUI上放置一个画布，并用.grid()来调整布局
    drawPic.f = Figure(figsize=(5, 4), dpi=100)
    drawPic.canvas = FigureCanvasTkAgg(drawPic.f, master=root)
    drawPic.canvas.draw()
    drawPic.canvas.get_tk_widget().grid(row=0, columnspan=3)
    drawPic()
    # 启动事件循环
    root.mainloop()


if __name__ == '__main__':
    run()
