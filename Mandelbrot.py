from PIL import Image, ImageTk, ImageColor, ImageFilter
#from numpy import interp
import numpy as np
import math
import time
import sys
import colorsys
import threading

import multiprocessing as mulp
import queue

import tkinter as tk

from mpmath import mp

import json
import base64

import argparse
import os

def genmandel(zoomxy, offsetx, offsety, maxiter, size, ItemQueue, ResultQueue, UseHighPrecision):
#    print("[Worker start]")
#    pixels = GlobalGenImage.load()
    while True:
        try:
            CurrentRow = ItemQueue.get(block=True,timeout=3)
        except queue.Empty:
#            print("[Worker Exit]")
            sys.exit(0)

        y = CurrentRow
        if UseHighPrecision:
            #print(f"Row {y}: {round(y/size*100,2)}%")
            pass
        else:
            if y%5==0:
                #print(f"Row {y}: {round(y/size*100,2)}%")
                pass
        row = [0]*(size+1)
        for x in range(size):
            rangemidx = 2 * (1/zoomxy)
            rangemidy = 2 * (1/zoomxy)
            r1 = -1*rangemidx + offsetx
            r2 = 1*rangemidx + offsetx
            r3 = -1*rangemidy + offsety
            r4 = 1*rangemidy + offsety
            pixran = size
            
            if UseHighPrecision:
                rangemidx = 2 * (mp.mpf(1)/zoomxy)
                rangemidy = 2 * (mp.mpf(1)/zoomxy)
                r1 = -1*rangemidx + offsetx
                r2 = 1*rangemidx + offsetx
                r3 = -1*rangemidy + offsety
                r4 = 1*rangemidy + offsety
                cr = (mp.mpf(x/pixran) * (r2-r1)) + r1
                ci = (mp.mpf(y/pixran) * (r3-r4)) + r4
                c = mp.mpc(cr,ci)
            else:
                c = complex(np.interp(x, [0,pixran-1], [r1,r2]), np.interp(y, [0,pixran-1], [r3,r4]))

            #print(f"Pixel {x},{y} at {c.real},{c.imag}")
            n = 0
            z = complex(0,0)
            while n < maxiter and z.real < (2+abs(offsetx)) and z.imag < (2+abs(offsety)): #Other Escape functions!
                z = z*z + c
                #print(f"Iter {n} val {z.real},{z.imag}")
                n+=1
            
            if n == maxiter:
                #pixels[x,y] = (0,0,0)
                #pixels[x,y] = (0)
                row[x] = 0
            else:
                ###Implement Palletes!###
                PixVal = int((n/maxiter)* 255)
                coloff = 20
                PixOffset = (PixVal + coloff) % 255
                row[(x+1)] = (PixOffset)
        row[0] = y
 #       print(row)
        ResultQueue.put(row)
        ItemQueue.task_done()

#    im.show()
#    im = im.convert(mode="RGB")
# im.show()
#    im.save(f"MandelRGB{str(size)}.png")
#    im.save(input("Save as:"))


def thread_gennew(label, x, y):
    global zoom
    global offx, offy
    global generating
    global maxiter
    global GlobQtImage
    zoom *= 2
    #maxiter += int(zoom*10)
    
    if UseHighPrecision:
        rangemid = 2 * (mp.mpf(1)/zoom)
        offx = ((mp.mpf(x/size) * ((rangemid)-(-1*rangemid)) + (-1*rangemid)) *2)+offx
        offy = ((mp.mpf(y/size) * ((rangemid)-(-1*rangemid)) + (-1*rangemid)) *2)+offy
    else:
        rangemid = 2 * (1/zoom)
        offx = (np.interp(x, [0,size], [-1*rangemid,rangemid]) * 2)+offx
        offy = (np.interp(y, [0,size], [-1*rangemid,rangemid]) * 2)+offy
        print(offx, offy)

    print(f"Generating Mandelbrot zoom X {offx} Y {offy} Zoom {zoom} with {maxiter} Iterations")
    
    if UseHighPrecision == False:
        posdict = {"x": offx, "y":offy, "zoom": zoom}
        base64dec = json.dumps(posdict)
        base64enc = base64.b64encode(bytes(base64dec, "utf-8"))
    else:
        posdict = {"x": str(offx), "y":str(offy), "zoom": str(zoom)}
        base64dec = json.dumps(posdict)
        base64enc = base64.b64encode(bytes(base64dec, "utf-8"))
        
        
    print("To resume from this position, please copy/store this string:")
    print(str(base64enc)[2:-1])    

    GenQueue = mulp.JoinableQueue()
    if args["nointerlace"] == False:
        #Interlacing every 8 Lines
        for i in range(gensize//8):
            GenQueue.put(i*8)
        #Interlacing every 4 Lines
        for i in range(gensize//8):
            GenQueue.put(i*8+4)
        #Interlacing every 2 Lines
        for i in range(gensize//4):
            GenQueue.put(i*4+2)
        #Filling every Line
        for i in range(gensize//4):
            GenQueue.put(i*4+1)
            GenQueue.put(i*4+3)
    else:
        for i in range(gensize):
            GenQueue.put(i)
    
    t = []
    ResultQueue = mulp.Queue()
    print(f"Using {mulp.cpu_count()} threads")
    for i in range(mulp.cpu_count()):
        t.append(mulp.Process(target=genmandel, args=(zoom, offx, offy,maxiter,gensize, GenQueue, ResultQueue, UseHighPrecision)))
        t[i].start()

    #GenQueue.join()
    print("Threads Done")

    FinImage = Image.new("RGB", (gensize,gensize))
    pixels = FinImage.load()
    updatecounter = 0
    for i in range(gensize):
        data = ResultQueue.get(timeout=30)
        y = data[0]
        for x in range(gensize):
            hsv = colorsys.hsv_to_rgb(data[x+1]/255, 1, 1)
            if data[x+1] == 0:
                pixels[x,y] = (0,0,0)
            else:
                pixels[x,y] = (int(hsv[0]*255), int(hsv[1]*255), int(hsv[2]*255))

        updatecounter +=1
        if updatecounter%5==0:
            genim = FinImage.resize((size,size),Image.BILINEAR)
            #genim = genim.filter(ImageFilter.GaussianBlur(1))
            tkim = ImageTk.PhotoImage(genim)
            label.update(tkim)
            print(f"Row {y}: {round(updatecounter/gensize*100,2)}%")
 #   GlobalGenImage.save(f"Mandel{str(size)}.png")
  #  FinImage.show()
    
    genim = FinImage.resize((size,size),Image.BICUBIC)
    tkim = ImageTk.PhotoImage(genim)
    label.update(tkim)


    if False:
        coloroff = 1
        framecount = 0
        while framecount < 400:
            newimage = FinImage.copy()
            pixels = newimage.load()
            for y in range(FinImage.height):
                if y%256==0:
                    print("Color Row", y)
                for x in range(FinImage.width):
                    curpix = pixels[x,y]
                    if curpix == (0,0,0):
                        pass
                    else:
                        pixrgb = colorsys.rgb_to_hsv(curpix[0]/256,curpix[1]/256,curpix[2]/256)
                        offset = (pixrgb[0] + (coloroff/256)) % 1
                        newhsv = colorsys.hsv_to_rgb(offset,1,1)
                        pixels[x,y] = (int(newhsv[0]*256), int(newhsv[1]*256), int(newhsv[2]*256))

            FinImage.save(f"MandelVideo\img_{framecount:03d}.png")
            genim = FinImage.resize((size,size),Image.BICUBIC)
            tkim = ImageTk.PhotoImage(genim)
            label.update(tkim)
            coloroff += 1
            print(coloroff)
            framecount += 1

    
    print("Finished")
    print("To resume from this position, please copy/store this string:")
    print(str(base64enc)[2:-1])  
    generating = False

def clickevent(event):
    global generating
    if generating == False:
        generating = True
        x = event.x
        y = event.y
        print(f"Clicked x:{x} y:{y}")
        t = threading.Thread(target=thread_gennew, args=(label, x, y))
        t.start()
    else:
        print("Already generating, please wait!")

class UpdatingLabel:
    def __init__(self,parent):
        self.parent = parent
        self.label = tk.Label(self.parent)
        self.label['image'] = ImageTk.PhotoImage(Image.new("RGB", (size,size)))
        self.label.pack()
        self.label.bind("<Button-1>", clickevent)
       # self.update()

    def update(self, newimagetk):
        self.label.configure(image=newimagetk)
        self.label.image = newimagetk

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Mandelbrot Viewer in Python')
    parser.add_argument('-w', dest="winsize", default=512, type=int, required=False, help="Mandelbrot Window size in pixels", metavar="size")   #Window size
    parser.add_argument('-s', dest="gensize", default=512, type=int, required=False, help="Mandelbrot Generating Size", metavar="size")   #Generating size
    parser.add_argument('-i', dest="iter", default=100, type=int, required=False, help="Mandelbrot Iterations", metavar="iterations")   #Iterations?

    parser.add_argument('--high_prec', dest="prec", action="store_true", default=False, required=False, help="Use High precisions")   #High Precision
    parser.add_argument('--prec_bits', dest="precbits", default=64, type=int, required=False, help="If using High Precision, precision in bits", metavar="bits")   #High Precision Bits
    parser.add_argument('--nointerlace', dest="nointerlace",action="store_true", default=False, required=False, help="Disable Interlacing")
    args = vars(parser.parse_args())
    print(args)
    
    mp.prec = args["precbits"] #Floating Number Precision!
    mp.pretty = False

    UseHighPrecision = args["prec"]
    if UseHighPrecision:
        print(f"Using MpMath high Precision floats with {mp.prec} bit precision ({mp.dps} decimal places), expect reduced performance!")
        #print(mp)
    else:
        print(f"Using Standart Python Precision with {sys.float_info.mant_dig} bit floats")

    
    size = args["winsize"]
    gensize = args["gensize"]
    maxiter = args["iter"]
    #gensize = int(input("Size: "))

    yn = input("Do you want to resume from a previous position? [y/n]: ").lower()
    if yn=="y":
        base64enc = bytes(input("Please enter the copied string: "), "utf-8")
    #    try:
        base64dec = base64.b64decode(base64enc, validate=True)
        
        posdict = json.loads(base64dec)
        print(posdict)
        strzoom = posdict["zoom"]
        stroffx = posdict["x"]
        stroffy = posdict["y"]
    else:
        if yn=="n":
            strzoom = "0.5"
            stroffx = "-1"
            stroffy = "0"
        else:
            print("\nPlease enter Y or N!")
            time.sleep(1)
            sys.exit(1)
    
    if UseHighPrecision:
        zoom = mp.mpf(strzoom)
        offx = mp.mpf(stroffx)
        offy = mp.mpf(stroffy)
        print(offx, offy)
    else:
        zoom = float(strzoom)
        offx = float(stroffx)
        offy = float(stroffy)
    generating = True

    root = tk.Tk()
    root.resizable(False, False)
    root.title("NetherStar Mandelbrot")
    im = Image.new("RGB", (size,size))
    pixels = im.load()
    for x in range(size):
        for y in range(size):
            pixels[x,y] = (0,0,0)
    tkim = ImageTk.PhotoImage(im)
    label = UpdatingLabel(root)
    

    t = threading.Thread(target=thread_gennew, args=(label, int(size/2), int(size/2) ) )
    t.start()

    root.mainloop()
    print("Exit")
    os._exit(1)
