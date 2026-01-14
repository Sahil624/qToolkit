from global_variables import *

class DragManager():
    def __init__(self, get_mode):
        self.get_mode = get_mode

    def add_dragable(self, node, canvas):
        self.node = node
        self.node_id = node.oval_id
        self.canvas = canvas
        canvas.tag_bind(self.node_id, f"<ButtonPress-1>", self.on_start)
        canvas.tag_bind(self.node_id, "<B1-Motion>", self.on_drag)
        canvas.tag_bind(self.node_id,"<ButtonRelease-1>", self.on_drop)
        #widget.configure(cursor="hand1")

    def on_start(self, event):
        # you could use this method to create a floating window
        # that represents what is being dragged.
        if self.get_mode() == rearrange:
            print('in start')
        pass

    def on_drag(self, event):
        # you could use this method to move a floating window that
        # represents what you're dragging
        # print('ffff',self.get_mode())
        if self.get_mode() == rearrange:
            sx, sy, ex, ey = self.canvas.coords(self.node_id)
            print(self.node.connections)
            self.canvas.move(self.node_id,event.x - (sx+ex)/2, event.y - (sy+ey)/2)
            connections = self.node.connections
            snex = (sx+ex)/2
            sney = (sy+ey)/2
            print(connections)
            for item in connections:
                if item != 0:
                    scx, scy, ecx, ecy = self.canvas.coords(item)
                    snx, sny, enx, eny = self.canvas.coords(self.node_id)
                    print(self.node.position, scx, scy, ecx, ecy, snx, sny, enx, eny )
                    if scx == self.node.position[0] and scy == self.node.position[1]:
                        scx, scy, ecx, ecy = self.canvas.coords(item)
                        self.canvas.coords(item, snex, sney, ecx, ecy)
                    else:
                        scx, scy, ecx, ecy = self.canvas.coords(item)
                        self.canvas.coords(item, scx, scy, snex, sney)
            self.node.position_update(snex, 0)
            self.node.position_update(sney, 1)
        pass

    def on_drop(self, event):
        # find the widget under the cursor
        if self.get_mode() == rearrange:
            print('in drop')
            x,y = event.widget.winfo_pointerxy()
            target = event.widget.winfo_containing(x,y)
            try:
                target.configure(image=event.widget.cget("image"))
            except:
                pass