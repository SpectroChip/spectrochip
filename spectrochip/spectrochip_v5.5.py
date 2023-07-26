print("Starting up...")
version = "V5.5"

print("Importing...")
from PyQt5 import QtCore, QtGui, QtWidgets
from scipy import signal
import numpy as np
import pyqtgraph as pg
import sys, configparser, cv2, threading, subprocess, time, os,serial
import pandas as pd
print("Import Complete")

np.set_printoptions(threshold = sys.maxsize)

config = configparser.ConfigParser()             #configparser 文件解析器
config.read('config.ini')

###################################### Initialization #####################################

# 相機參數
shutter = config['default']['shutter']          #max 1,000,000
anolog_gain = config['default']['anolog_gain']  #max 100,000,000
digital_gain = config['default']['digital_gain']
st_max = 1000000
ag_max = 10000000

# 坐標軸參數
x = config['default']['x']
y = config['default']['y']
deltax = config['default']['deltax']
deltay = config['default']['deltay']
x_axis_min = config['graph']['x_axis_min']
x_axis_max = config['graph']['x_axis_max']
y_axis_min = config['graph']['y_axis_min']
y_axis_max = config['graph']['y_axis_max']

# 波長校正係數
a3 = config['wavelength_calibration']['a3']
a2 = config['wavelength_calibration']['a2']
a1 = config['wavelength_calibration']['a1']
a0 = config['wavelength_calibration']['a0']
e3 = config['wavelength_calibration']['e3']
e2 = config['wavelength_calibration']['e2']
e1 = config['wavelength_calibration']['e1']
e0 = config['wavelength_calibration']['e0']

########### 家峰 function 宣告 global 參數及初始化 #################

# 判斷是哪個 window 
window_num = 1 

# AutoScaling 參數
st1 = 0
st2 = 0
I1 = 0
I2 = 0

I_thr = 0
I_thr_top = 0
I_thr_bottom = 0
max_value = 0
goal_st = 0

I_max = config['auto_scaling']['I_max']
I_thr_percentage = config['auto_scaling']['I_thr_percentage']
I_thr_tolerance = config['auto_scaling']['I_thr_tolerance']

# 拍照次數
num_scan = config['numof_scan']['numberof_scan']

# SG參數
w_length = config['sgfilter']['window_length']
poly_order = config['sgfilter']['polyorder']

# 模式
mode = 0       
auto_mode = 0
roi_mode = 1
flag = 0

new_y0 = 0
c_draw_wgraph = 0

# 拍照資料存取
wdata = []       # 波長
numb_ofscan = [] # 連續拍照資料
ncolmean = []    # 連續拍照資料做平均

# Auto find peak
hg_max = 0
hg_data = []
hg_peak = []
hg_peaks = []
ar_data = []
ar_peak = []
ar_peaks = []
dist = 0

hgar_temp = [0] * 10

########### Transmission function 宣告 global 參數及初始化 #################
bo_mode = 0
t_button_check = 1                                             # 沒有 t1 限制 
spectro_mode = 0                                               # Ref or Sample
# 存取光譜數據
Dark_data = []
refSpectro_data = []
refsmd_data = []
refmall_data = []                                               # 都扣完後的
sampleSpectro_data = []
samsmd_data = []
sammall_data = []
trans_data = []
d_lambda = []
sg_img = []

sg_timg = []
# 設定 serial 參數
ser = serial.Serial()
ser.baudrate = 115200
ser.bytesize = serial.EIGHTBITS 	#number of bits per bytes
ser.parity = serial.PARITY_NONE 	#set parity check
ser.stopbits = serial.STOPBITS_ONE 	#number of stop bits
ser.timeout = 0.5           	    #non-block read 0.5s
ser.writeTimeout = 0  		        #timeout for write 0.5s
ser.xonxoff = False    			    #disable software flow control
ser.rtscts = False     			    #disable hardware (RTS/CTS) flow control
ser.dsrdtr = False     			    #disable hardware (DSR/DTR) flow control

class SignalCommunication(QtCore.QObject):
    new_image = QtCore.pyqtSignal()
    new_y0 = QtCore.pyqtSignal()
    new_data = QtCore.pyqtSignal()
    new_wdata = QtCore.pyqtSignal()
    new_goal_st =  QtCore.pyqtSignal()
    new_pixel = QtCore.pyqtSignal()
    bo_new_data = QtCore.pyqtSignal()

class Ui_mainwindow(object):
    def setupUi(self, mainwindow):
        print("Initialing...")
        mainwindow.setObjectName("mainwindow")
        mainwindow.resize(1310, 965)
        self.centralwidget = QtWidgets.QWidget(mainwindow)
        self.centralwidget.setObjectName("centralwidget")
        
        mainwindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(mainwindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 831, 21))
        self.menubar.setObjectName("menubar")
        mainwindow.setMenuBar(self.menubar)
        
        self.functionmenu = self.menubar.addMenu("Function")
        self.actionCalculate_wavelength = QtWidgets.QAction(mainwindow)
        self.actionCalculate_wavelength.setObjectName("actionCalculate_wavelength")
        
        self.functionmenu.addAction(self.actionCalculate_wavelength)
        
        self.transmission_mode = QtWidgets.QAction(mainwindow)
        self.transmission_mode.setObjectName("transmission_mode")
        self.functionmenu.addAction(self.transmission_mode)

        self.statusbar = QtWidgets.QStatusBar(mainwindow)
        self.statusbar.setObjectName("statusbar")
        mainwindow.setStatusBar(self.statusbar)
        
        self.camera_list = QtWidgets.QListView(self.centralwidget)
        self.camera_list.setGeometry(QtCore.QRect(70, 15, 380, 155))
        self.camera_list.setObjectName("camera_list")
        self.format_box = QtWidgets.QComboBox(self.centralwidget)
        self.format_box.setGeometry(QtCore.QRect(220, 20, 69, 22))
        self.format_box.setObjectName("format_box")
        self.format_box.addItem("")
        self.format_box.addItem("")
        self.shutter_edit = QtWidgets.QLineEdit(self.centralwidget)
        self.shutter_edit.setGeometry(QtCore.QRect(220, 50, 104, 31))
        self.shutter_edit.setObjectName("shutter_edit")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(110, 20, 100, 16))
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setGeometry(QtCore.QRect(110, 60, 100, 16))
        self.label_2.setObjectName("label_2")
        self.label_3 = QtWidgets.QLabel(self.centralwidget)
        self.label_3.setGeometry(QtCore.QRect(110, 100, 100, 16))
        self.label_3.setObjectName("label_3")
        self.label_4 = QtWidgets.QLabel(self.centralwidget)
        self.label_4.setGeometry(QtCore.QRect(110, 140, 100, 16))
        self.label_4.setObjectName("label_4")
        self.anologgain_edit = QtWidgets.QLineEdit(self.centralwidget)
        self.anologgain_edit.setGeometry(QtCore.QRect(220, 90, 104, 31))
        self.anologgain_edit.setObjectName("anologgain_edit")
        self.digitalgain_edit = QtWidgets.QLineEdit(self.centralwidget)
        self.digitalgain_edit.setGeometry(QtCore.QRect(220, 130, 104, 31))
        self.digitalgain_edit.setObjectName("digitalgain_edit")
        
        self.pixel_graph = pg.PlotWidget(self.centralwidget)
        self.pixel_graph.setGeometry(QtCore.QRect(145, 510, 500, 400))
        
        self.wavelength_graph = pg.PlotWidget(self.centralwidget)
        self.wavelength_graph.setGeometry(QtCore.QRect(660, 510, 500, 400))
        
        self.image_frame = QtWidgets.QLabel(self.centralwidget)
        self.image_frame.setGeometry(QtCore.QRect(470, 5, 300, 200)) 
        
        self.camera_start_list = QtWidgets.QListView(self.centralwidget)
        self.camera_start_list.setGeometry(QtCore.QRect(70, 425, 380, 75))
        self.camera_start_list.setObjectName("camera_start_list")
        self.start = QtWidgets.QPushButton(self.centralwidget)
        self.start.setGeometry(QtCore.QRect(100, 470, 75, 23))
        self.start.setObjectName("start")
        self.continue_checkbox = QtWidgets.QCheckBox('continuous',self.centralwidget)
        self.continue_checkbox.setGeometry(QtCore.QRect(220, 470, 100, 23))
        self.continue_checkbox.setLayoutDirection(QtCore.Qt.LeftToRight)
        
        self.pixel_list = QtWidgets.QListView(self.centralwidget)
        self.pixel_list.setGeometry(QtCore.QRect(5, 615, 130, 210))
        self.pixel_list.setObjectName("pixel_list")
        self.label_6 = QtWidgets.QLabel(self.centralwidget)
        self.label_6.setGeometry(QtCore.QRect(50, 620, 100, 16))
        self.label_6.setObjectName("label_6")
        self.auto_y_axis = QtWidgets.QRadioButton(self.centralwidget)
        self.auto_y_axis.setGeometry(QtCore.QRect(40, 670, 75, 23))
        self.auto_y_axis.setObjectName("auto_y_axis")
        self.fix_y_axis = QtWidgets.QRadioButton(self.centralwidget)
        self.fix_y_axis.setGeometry(QtCore.QRect(40, 690, 75, 23))
        self.fix_y_axis.setObjectName("fix_y_axis")
        self.Yaxis_max = QtWidgets.QLineEdit(self.centralwidget)
        self.Yaxis_max.setGeometry(QtCore.QRect(80, 640, 50, 31))
        self.Yaxis_max.setObjectName("Yaxis_max")
        self.Yaxis_min = QtWidgets.QLineEdit(self.centralwidget)
        self.Yaxis_min.setGeometry(QtCore.QRect(10, 640, 50, 31))
        self.Yaxis_min.setObjectName("Yaxis_min")
        self.x_axis_label = QtWidgets.QLabel(self.centralwidget)
        self.x_axis_label.setGeometry(QtCore.QRect(50, 720, 100, 16))
        self.x_axis_label.setObjectName("x_axis_label")
        self.Xaxis_min = QtWidgets.QLineEdit(self.centralwidget)
        self.Xaxis_min.setGeometry(QtCore.QRect(10, 740, 50, 31))
        self.Xaxis_min.setObjectName("Xaxis_min")
        self.Xaxis_max = QtWidgets.QLineEdit(self.centralwidget)
        self.Xaxis_max.setGeometry(QtCore.QRect(80, 740, 50, 31))
        self.Xaxis_max.setObjectName("Xaxis_max")
        self.auto_x_axis = QtWidgets.QRadioButton(self.centralwidget)
        self.auto_x_axis.setGeometry(QtCore.QRect(40, 780, 75, 23))
        self.auto_x_axis.setObjectName("auto_x_axis")
        self.fix_x_axis = QtWidgets.QRadioButton(self.centralwidget)
        self.fix_x_axis.setGeometry(QtCore.QRect(40, 800, 75, 23))
        self.fix_x_axis.setObjectName("fix_x_axis")
        
        self.wavelength_list = QtWidgets.QListView(self.centralwidget)
        self.wavelength_list.setGeometry(QtCore.QRect(1170, 615, 130, 210))
        self.wavelength_list.setObjectName("wavelength_list")
        self.w_x_axis_label = QtWidgets.QLabel(self.centralwidget)
        self.w_x_axis_label.setGeometry(QtCore.QRect(1215, 720, 100, 16))
        self.w_x_axis_label.setObjectName("w_x_axis_label")
        self.w_auto_x_axis = QtWidgets.QRadioButton(self.centralwidget)
        self.w_auto_x_axis.setGeometry(QtCore.QRect(1195, 780, 75, 23))
        self.w_auto_x_axis.setObjectName("w_auto_x_axis")
        self.w_fix_x_axis = QtWidgets.QRadioButton(self.centralwidget)
        self.w_fix_x_axis.setGeometry(QtCore.QRect(1195, 800, 75, 23))
        self.w_fix_x_axis.setObjectName("w_fix_x_axis")
        self.W_Xaxis_max = QtWidgets.QLineEdit(self.centralwidget)
        self.W_Xaxis_max.setGeometry(QtCore.QRect(1245, 740, 50, 31))
        self.W_Xaxis_max.setObjectName("W_Xaxis_max")
        self.W_Xaxis_min = QtWidgets.QLineEdit(self.centralwidget)
        self.W_Xaxis_min.setGeometry(QtCore.QRect(1175, 740, 50, 31))
        self.W_Xaxis_min.setObjectName("W_Xaxis_min")
        self.W_Yaxis_min = QtWidgets.QLineEdit(self.centralwidget)
        self.W_Yaxis_min.setGeometry(QtCore.QRect(1175, 640, 50, 31))
        self.W_Yaxis_min.setObjectName("W_Yaxis_min")
        self.W_Yaxis_max = QtWidgets.QLineEdit(self.centralwidget)
        self.W_Yaxis_max.setGeometry(QtCore.QRect(1245, 640, 50, 31))
        self.W_Yaxis_max.setObjectName("W_Yaxis_max")
        self.w_auto_y_axis = QtWidgets.QRadioButton(self.centralwidget)
        self.w_auto_y_axis.setGeometry(QtCore.QRect(1195, 670, 75, 23))
        self.w_auto_y_axis.setObjectName("w_auto_y_axis")
        self.w_fix_y_axis = QtWidgets.QRadioButton(self.centralwidget)
        self.w_fix_y_axis.setGeometry(QtCore.QRect(1195, 690, 75, 23))
        self.w_fix_y_axis.setObjectName("w_fix_y_axis")
        self.label_7 = QtWidgets.QLabel(self.centralwidget)
        self.label_7.setGeometry(QtCore.QRect(1215, 620, 100, 16))
        self.label_7.setObjectName("label_7")
        
        self.w_parameter_list = QtWidgets.QListView(self.centralwidget)
        self.w_parameter_list.setGeometry(QtCore.QRect(660, 265, 300, 220))
        self.w_parameter_list.setObjectName("w_parameter_list")
        self.w_parameter_label = QtWidgets.QLabel(self.centralwidget)
        self.w_parameter_label.setGeometry(QtCore.QRect(670, 270, 280, 16))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.w_parameter_label.setFont(font)
        self.w_parameter_label.setObjectName("w_parameter_label")
        
        self.a3_label = QtWidgets.QLabel(self.centralwidget)
        self.a3_label.setGeometry(QtCore.QRect(670, 300, 50, 16))
        self.a3_label.setObjectName("a3_label")
        self.a3 = QtWidgets.QLineEdit(self.centralwidget)
        self.a3.setGeometry(QtCore.QRect(700, 290, 80, 30))
        self.a3.setObjectName("a3")
        self.a2_label = QtWidgets.QLabel(self.centralwidget)
        self.a2_label.setGeometry(QtCore.QRect(670, 340, 50, 16))
        self.a2_label.setObjectName("a2_label")
        self.a2 = QtWidgets.QLineEdit(self.centralwidget)
        self.a2.setGeometry(QtCore.QRect(700, 330, 80, 30))
        self.a2.setObjectName("a2")
        self.a1_label = QtWidgets.QLabel(self.centralwidget)
        self.a1_label.setGeometry(QtCore.QRect(670, 380, 50, 16))
        self.a1_label.setObjectName("a1_label")
        self.a1 = QtWidgets.QLineEdit(self.centralwidget)
        self.a1.setGeometry(QtCore.QRect(700, 370, 80, 30))
        self.a1.setObjectName("a1")
        self.a0_label = QtWidgets.QLabel(self.centralwidget)
        self.a0_label.setGeometry(QtCore.QRect(670, 420, 50, 16))
        self.a0_label.setObjectName("a0_label")
        self.a0 = QtWidgets.QLineEdit(self.centralwidget)
        self.a0.setGeometry(QtCore.QRect(700, 410, 80, 30))
        self.a0.setObjectName("a0")
        
        self.e3_label = QtWidgets.QLabel(self.centralwidget)
        self.e3_label.setGeometry(QtCore.QRect(790, 300, 50, 16))
        self.e3_label.setObjectName("e3_label")
        self.e2_label = QtWidgets.QLabel(self.centralwidget)
        self.e2_label.setGeometry(QtCore.QRect(790, 340, 50, 16))
        self.e2_label.setObjectName("e2_label")
        self.e1_label = QtWidgets.QLabel(self.centralwidget)
        self.e1_label.setGeometry(QtCore.QRect(790, 380, 50, 16))
        self.e1_label.setObjectName("e1_label")
        self.e0_label = QtWidgets.QLabel(self.centralwidget)
        self.e0_label.setGeometry(QtCore.QRect(790, 420, 50, 16))
        self.e0_label.setObjectName("e0_label")
        self.e3 = QtWidgets.QLineEdit(self.centralwidget)
        self.e3.setGeometry(QtCore.QRect(810, 290, 80, 30))
        self.e3.setObjectName("e3")
        self.e2 = QtWidgets.QLineEdit(self.centralwidget)
        self.e2.setGeometry(QtCore.QRect(810, 330, 80, 30))
        self.e2.setObjectName("e2")
        self.e1 = QtWidgets.QLineEdit(self.centralwidget)
        self.e1.setGeometry(QtCore.QRect(810, 370, 80, 30))
        self.e1.setObjectName("e1")
        self.e0 = QtWidgets.QLineEdit(self.centralwidget)
        self.e0.setGeometry(QtCore.QRect(810, 410, 80, 30))
        self.e0.setObjectName("e0")
        
        self.w_enter_button = QtWidgets.QPushButton(self.centralwidget)
        self.w_enter_button.setGeometry(QtCore.QRect(670, 450, 120, 30))
        self.w_enter_button.setObjectName("w_enter_button")
        
        self.max_shutter_label = QtWidgets.QLabel(self.centralwidget)
        self.max_shutter_label.setGeometry(QtCore.QRect(330, 60, 150, 16))
        self.max_shutter_label.setObjectName("max_shutter_label")
        self.max_anologgain_label = QtWidgets.QLabel(self.centralwidget)
        self.max_anologgain_label.setGeometry(QtCore.QRect(330, 100, 120, 16))
        self.max_anologgain_label.setObjectName("max_anologgain_label")
        self.max_digitalgain_label = QtWidgets.QLabel(self.centralwidget)
        self.max_digitalgain_label.setGeometry(QtCore.QRect(330, 140, 120, 16))
        self.max_digitalgain_label.setObjectName("max_digitalgain_label")
        
        self.ROI_list = QtWidgets.QListView(self.centralwidget)
        self.ROI_list.setGeometry(QtCore.QRect(70, 175, 380, 75))
        self.ROI_list.setObjectName("ROI_list")
        self.auto_roi_label = QtWidgets.QLabel(self.centralwidget)
        self.auto_roi_label.setGeometry(QtCore.QRect(125, 225, 150, 16))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.auto_roi_label.setFont(font)
        self.auto_roi_label.setObjectName("auto_roi_label")
        self.auto_roi = QtWidgets.QRadioButton(self.centralwidget)
        self.auto_roi.setGeometry(QtCore.QRect(210, 220, 75, 23))
        self.auto_roi.setObjectName("auto_roi")
        self.manual_roi = QtWidgets.QRadioButton(self.centralwidget)
        self.manual_roi.setGeometry(QtCore.QRect(290, 220, 75, 23))
        self.manual_roi.setObjectName("manual_roi")
        self.label_5 = QtWidgets.QLabel(self.centralwidget)
        self.label_5.setGeometry(QtCore.QRect(80, 190, 150, 16))
        self.label_5.setObjectName("label_5")
        self.x0 = QtWidgets.QLineEdit(self.centralwidget)
        self.x0.setGeometry(QtCore.QRect(210, 180, 50, 30))
        self.x0.setObjectName("x0")
        self.y0 = QtWidgets.QLineEdit(self.centralwidget)
        self.y0.setGeometry(QtCore.QRect(270, 180, 50, 30))
        self.y0.setObjectName("y0")
        self.x1 = QtWidgets.QLineEdit(self.centralwidget)
        self.x1.setGeometry(QtCore.QRect(330, 180, 50, 30))
        self.x1.setObjectName("x1")
        self.y1 = QtWidgets.QLineEdit(self.centralwidget)
        self.y1.setGeometry(QtCore.QRect(390, 180, 50, 30))
        self.y1.setObjectName("y1")
        
        self.Auto_Scaling_List = QtWidgets.QListView(self.centralwidget)
        self.Auto_Scaling_List.setGeometry(QtCore.QRect(70, 260, 380, 155))
        self.Auto_Scaling_List.setObjectName("Auto_Scaling_List")
        
        self.auto_scaling_label = QtWidgets.QLabel(self.centralwidget)
        self.auto_scaling_label.setGeometry(QtCore.QRect(100, 270, 150, 16))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.auto_scaling_label.setFont(font)
        self.auto_scaling_label.setObjectName("auto_scaling_label")
        self.auto_scaling = QtWidgets.QPushButton(self.centralwidget)
        self.auto_scaling.setGeometry(QtCore.QRect(210, 270, 75, 23))
        self.auto_scaling.setObjectName("auto_scaling")
        self.I_max_label = QtWidgets.QLabel(self.centralwidget)
        self.I_max_label.setGeometry(QtCore.QRect(100, 310, 150, 16))
        self.I_max_label.setObjectName("I_max_label")
        self.I_max_label1 = QtWidgets.QLabel(self.centralwidget)
        self.I_max_label1.setGeometry(QtCore.QRect(275, 310, 150, 16))
        self.I_max_label1.setObjectName("I_max_label1")
        self.I_thr_percentage_label = QtWidgets.QLabel(self.centralwidget)
        self.I_thr_percentage_label.setGeometry(QtCore.QRect(100, 350, 150, 16))
        self.I_thr_percentage_label.setObjectName("I_thr_percentage_label")
        self.I_thr_percentage_label1 = QtWidgets.QLabel(self.centralwidget)
        self.I_thr_percentage_label1.setGeometry(QtCore.QRect(275, 350, 150, 16))
        self.I_thr_percentage_label1.setObjectName("I_thr_percentage_label1")
        self.I_thr_tolerance_label = QtWidgets.QLabel(self.centralwidget)
        self.I_thr_tolerance_label.setGeometry(QtCore.QRect(100, 390, 150, 16))
        self.I_thr_tolerance_label.setObjectName("I_thr_tolerance_label")
        self.I_thr_tolerance_label1 = QtWidgets.QLabel(self.centralwidget)
        self.I_thr_tolerance_label1.setGeometry(QtCore.QRect(275, 390, 150, 16))
        self.I_thr_tolerance_label1.setObjectName("I_thr_tolerance_label1")
        
        self.I_max_edit = QtWidgets.QLineEdit(self.centralwidget)
        self.I_max_edit.setGeometry(QtCore.QRect(220, 300, 50, 30))
        self.I_max_edit.setObjectName("I_max_edit")
        self.I_thr_percentage_edit = QtWidgets.QLineEdit(self.centralwidget)
        self.I_thr_percentage_edit.setGeometry(QtCore.QRect(220, 340, 50, 30))
        self.I_thr_percentage_edit.setObjectName("I_thr_percentage_edit")
        self.I_thr_tolerance_edit = QtWidgets.QLineEdit(self.centralwidget)
        self.I_thr_tolerance_edit.setGeometry(QtCore.QRect(220, 380, 50, 30))
        self.I_thr_tolerance_edit.setObjectName("I_thr_tolerance_edit")
        
        self.numberof_scan_label = QtWidgets.QLabel(self.centralwidget)
        self.numberof_scan_label.setGeometry(QtCore.QRect(100, 435, 150, 16))
        self.numberof_scan_label.setObjectName("numberof_scan_label")
        self.numberof_scan_label1 = QtWidgets.QLabel(self.centralwidget)
        self.numberof_scan_label1.setGeometry(QtCore.QRect(275, 435, 150, 16))
        self.numberof_scan_label1.setObjectName("numberof_scan_label1")
        self.numberof_scan_edit = QtWidgets.QLineEdit(self.centralwidget)
        self.numberof_scan_edit.setGeometry(QtCore.QRect(220, 430, 50, 30))
        self.numberof_scan_edit.setObjectName("numberof_scan_edit")
        
        self.camera_spec_list = QtWidgets.QListView(self.centralwidget)
        self.camera_spec_list.setGeometry(QtCore.QRect(790, 15, 190, 110))
        self.camera_spec_list.setObjectName("camera_spec_list")
        self.cameraspec_label = QtWidgets.QLabel(self.centralwidget)
        self.cameraspec_label.setGeometry(QtCore.QRect(800, 20, 150, 16))
        self.cameraspec_label.setObjectName("cameraspec_label")
        self.cameraname_label = QtWidgets.QLabel(self.centralwidget)
        self.cameraname_label.setGeometry(QtCore.QRect(800, 40, 150, 16))
        self.cameraname_label.setObjectName("cameraname_label")
        self.camerawidth_label = QtWidgets.QLabel(self.centralwidget)
        self.camerawidth_label.setGeometry(QtCore.QRect(800, 60, 200, 16))
        self.camerawidth_label.setObjectName("camerawidth_label")
        self.cameraheight_label = QtWidgets.QLabel(self.centralwidget)
        self.cameraheight_label.setGeometry(QtCore.QRect(800, 80, 200, 16))
        self.cameraheight_label.setObjectName("cameraheight_label")
        self.camerapixelsize_label = QtWidgets.QLabel(self.centralwidget)
        self.camerapixelsize_label.setGeometry(QtCore.QRect(800, 100, 200, 16))
        self.camerapixelsize_label.setObjectName("camerapixelsize_label")
        
        self.sg_list = QtWidgets.QListView(self.centralwidget)
        self.sg_list.setGeometry(QtCore.QRect(470, 265, 150, 115))
        self.sg_list.setObjectName("sg_list")
        self.sg_filter_checkbox = QtWidgets.QCheckBox(self.centralwidget)
        self.sg_filter_checkbox.setGeometry(QtCore.QRect(480, 270, 95, 16))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.sg_filter_checkbox.setFont(font)
        self.sg_filter_checkbox.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.sg_filter_checkbox.setObjectName("sg_filter_checkbox")
        self.window_length_label = QtWidgets.QLabel(self.centralwidget)
        self.window_length_label.setGeometry(QtCore.QRect(480, 310, 100, 16))
        self.window_length_label.setObjectName("window_length_label")
        self.polyorder_label = QtWidgets.QLabel(self.centralwidget)
        self.polyorder_label.setGeometry(QtCore.QRect(480, 350, 100, 16))
        self.polyorder_label.setObjectName("polyorder_label")
        self.window_length_edit = QtWidgets.QLineEdit(self.centralwidget)
        self.window_length_edit.setGeometry(QtCore.QRect(560, 300, 50, 30))
        self.window_length_edit.setObjectName("window_length_edit")
        self.polyorder_edit = QtWidgets.QLineEdit(self.centralwidget)
        self.polyorder_edit.setGeometry(QtCore.QRect(560, 340, 50, 30))
        self.polyorder_edit.setObjectName("polyorder_edit")
        
        self.default_list = QtWidgets.QListView(self.centralwidget)
        self.default_list.setGeometry(QtCore.QRect(990, 15, 220, 100))
        self.default_list.setObjectName("default_list")
        
        self.changedefault_label = QtWidgets.QLabel(self.centralwidget)
        self.changedefault_label.setGeometry(QtCore.QRect(1000, 20, 200, 16))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.changedefault_label.setFont(font)
        self.changedefault_label.setObjectName("changedefault_label")
        self.roi_default_checkbox = QtWidgets.QCheckBox(self.centralwidget)
        self.roi_default_checkbox.setGeometry(QtCore.QRect(1000, 40, 95, 16))
        self.roi_default_checkbox.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.roi_default_checkbox.setObjectName("roi_default_checkbox")
        self.wavelength_parameter_checkbox = QtWidgets.QCheckBox(self.centralwidget)
        self.wavelength_parameter_checkbox.setGeometry(QtCore.QRect(1000, 60, 200, 16))
        self.wavelength_parameter_checkbox.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.wavelength_parameter_checkbox.setObjectName("wavelength_parameter_checkbox")
        self.cahnge_btn = QtWidgets.QPushButton(self.centralwidget)
        self.cahnge_btn.setGeometry(QtCore.QRect(1000, 80, 75, 25))
        self.cahnge_btn.setObjectName("cahnge_btn")
        
        self.save_list = QtWidgets.QListView(self.centralwidget)
        self.save_list.setGeometry(QtCore.QRect(1090, 265, 170, 215))
        self.save_list.setObjectName("save_list")
        self.save_label = QtWidgets.QLabel(self.centralwidget)
        self.save_label.setGeometry(QtCore.QRect(1100, 270, 150, 16))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.save_label.setFont(font)
        self.save_label.setObjectName("save_label")
        self.save_rd_data_checkbox = QtWidgets.QCheckBox(self.centralwidget)
        self.save_rd_data_checkbox.setGeometry(QtCore.QRect(1100, 290, 95, 16))
        self.save_rd_data_checkbox.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.save_rd_data_checkbox.setObjectName("save_rd_data_checkbox")
        self.save_sg_data_checkbox = QtWidgets.QCheckBox(self.centralwidget)
        self.save_sg_data_checkbox.setGeometry(QtCore.QRect(1100, 310, 95, 16))
        self.save_sg_data_checkbox.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.save_sg_data_checkbox.setObjectName("save_sg_data_checkbox")
        self.save_file_label = QtWidgets.QLabel(self.centralwidget)
        self.save_file_label.setGeometry(QtCore.QRect(1100, 330, 150, 16))
        self.save_file_label.setObjectName("save_file_label")
        self.save_file_edit = QtWidgets.QLineEdit(self.centralwidget)
        self.save_file_edit.setGeometry(QtCore.QRect(1100, 350, 150, 31))
        self.save_file_edit.setObjectName("save_file_edit")
        self.browse_file_label = QtWidgets.QLabel(self.centralwidget)
        self.browse_file_label.setGeometry(QtCore.QRect(1100, 390, 150, 16))
        self.browse_file_label.setObjectName("browse_file_label")
        self.browse_file_edit = QtWidgets.QLineEdit(self.centralwidget)
        self.browse_file_edit.setGeometry(QtCore.QRect(1100, 410, 150, 31))
        self.browse_file_edit.setObjectName("browse_file_edit")
        self.browse_save_button = QtWidgets.QPushButton(self.centralwidget)
        self.browse_save_button.setGeometry(QtCore.QRect(1100, 450, 75, 25))
        self.browse_save_button.setObjectName("browse_save_button")
        self.save_function_button = QtWidgets.QPushButton(self.centralwidget)
        self.save_function_button.setGeometry(QtCore.QRect(1180, 450, 75, 25))
        self.save_function_button.setObjectName("save_function_button")
        
        self.roi_buttongroup = QtWidgets.QButtonGroup(mainwindow)
        self.roi_buttongroup.addButton(self.auto_roi)
        self.roi_buttongroup.addButton(self.manual_roi)
        self.xaxis_buttongroup = QtWidgets.QButtonGroup(mainwindow)
        self.xaxis_buttongroup.addButton(self.fix_x_axis)
        self.xaxis_buttongroup.addButton(self.auto_x_axis)
        self.yaxis_buttongroup = QtWidgets.QButtonGroup(mainwindow)
        self.yaxis_buttongroup.addButton(self.fix_y_axis)
        self.yaxis_buttongroup.addButton(self.auto_y_axis)
        self.w_xaxis_buttongroup = QtWidgets.QButtonGroup(mainwindow)
        self.w_xaxis_buttongroup.addButton(self.w_fix_x_axis)
        self.w_xaxis_buttongroup.addButton(self.w_auto_x_axis)
        self.w_yaxis_buttongroup = QtWidgets.QButtonGroup(mainwindow)
        self.w_yaxis_buttongroup.addButton(self.w_fix_y_axis)
        self.w_yaxis_buttongroup.addButton(self.w_auto_y_axis)
        
        self.retranslateUi(mainwindow)
        QtCore.QMetaObject.connectSlotsByName(mainwindow)
        # UI 介面連接 function
        self.actionCalculate_wavelength.triggered.connect(self.w_cal_button_clicked)
        self.transmission_mode.triggered.connect(self.transmission_window_show)
        self.start.clicked.connect(self.start_clicked)
        self.fix_x_axis.clicked.connect(self.x_axis_clicked)    
        self.auto_x_axis.clicked.connect(self.x_axis_clicked)    
        self.fix_y_axis.clicked.connect(self.y_axis_clicked)
        self.auto_y_axis.clicked.connect(self.y_axis_clicked)
        self.w_auto_x_axis.clicked.connect(self.w_x_axis_clicked)    
        self.w_fix_x_axis.clicked.connect(self.w_x_axis_clicked)    
        self.w_auto_y_axis.clicked.connect(self.w_y_axis_clicked)    
        self.w_fix_y_axis.clicked.connect(self.w_y_axis_clicked)    
        self.auto_scaling.clicked.connect(self.auto_scaling_clicked)    
        self.auto_roi.clicked.connect(self.auto_roi_clicked)    
        self.manual_roi.clicked.connect(self.manual_roi_clicked)       
        self.cahnge_btn.clicked.connect(self.change_btn_clicked)    
        self.w_enter_button.clicked.connect(self.w_enter_button_clicked)    
        self.browse_save_button.clicked.connect(self.browse_function_button_clicked)    
        self.save_function_button.clicked.connect(self.save_function_button_clicked)    
        
        self.continue_checkbox.toggled.connect(self.continue_checkbox_check)
        self.sg_filter_checkbox.toggled.connect(self.sg_filter_checkbox_check)
        self.save_rd_data_checkbox.toggled.connect(self.save_data_check)
        self.save_sg_data_checkbox.toggled.connect(self.save_data_check)
            
        self.Xaxis_min.textChanged[str].connect(self.x_axis_fix)
        self.Xaxis_max.textChanged[str].connect(self.x_axis_fix)
        self.Yaxis_min.textChanged[str].connect(self.y_axis_fix)
        self.Yaxis_max.textChanged[str].connect(self.y_axis_fix)
        self.W_Xaxis_min.textChanged[str].connect(self.w_x_axis_fix)
        self.W_Xaxis_max.textChanged[str].connect(self.w_x_axis_fix)
        self.W_Yaxis_min.textChanged[str].connect(self.w_y_axis_fix)
        self.W_Yaxis_max.textChanged[str].connect(self.w_y_axis_fix)
        self.x0.textChanged[str].connect(self.roi_change)
        self.y0.textChanged[str].connect(self.roi_change)
        self.x1.textChanged[str].connect(self.roi_change)
        self.y1.textChanged[str].connect(self.roi_change)
        self.I_max_edit.textChanged[str].connect(self.auto_scaling_paremeter_change)
        self.I_thr_percentage_edit.textChanged[str].connect(self.auto_scaling_paremeter_change)
        self.I_thr_tolerance_edit.textChanged[str].connect(self.auto_scaling_paremeter_change)
        self.numberof_scan_edit.textChanged[str].connect(self.scan_number_change)
        self.shutter_edit.textChanged[str].connect(self.shutter_change)
        self.window_length_edit.textChanged[str].connect(self.sg_change)
        self.polyorder_edit.textChanged[str].connect(self.sg_change)
        
        signalComm.new_image.connect(self.update_image)
        signalComm.new_y0.connect(self.update_y0)
        signalComm.new_data.connect(self.update_data)
        signalComm.new_wdata.connect(self.update_wdata)
        signalComm.new_goal_st.connect(self.update_st)
        
        self.statusbar.showMessage("DONE")
                
    def retranslateUi(self, mainwindow):
        global I_max, I_thr_percentage, I_thr_tolerance, I_thr, I_thr_top, I_thr_bottom
        
        _translate = QtCore.QCoreApplication.translate
        mainwindow.setWindowTitle(_translate("mainwindow", "Spectrochip "+version))
        self.label.setText(_translate("mainwindow", "Image Format"))
        self.format_box.setItemText(0, _translate("mainwindow", "BMP"))
        self.format_box.setItemText(1, _translate("mainwindow", "JPG"))
        self.label_2.setText(_translate("mainwindow", "Shutter"))
        self.label_3.setText(_translate("mainwindow", "Anolog Gain"))
        self.label_4.setText(_translate("mainwindow", "Digital Gain"))
        self.label_5.setText(_translate("mainwindow", "ROI : X0 Y0 X1 Y1"))
        self.image_frame.setText(_translate("mainwindow", "TextLabel"))
        self.start.setText(_translate("mainwindow", "START"))
        self.continue_checkbox.setText(_translate("mainwindow", "coninuous"))
        self.label_6.setText(_translate("mainwindow", "Y Axis"))
        self.auto_y_axis.setText(_translate("mainwindow", "AUTO"))
        self.fix_y_axis.setText(_translate("mainwindow", "FIX"))
        self.x_axis_label.setText(_translate("mainwindow", "X Axis"))
        self.auto_x_axis.setText(_translate("mainwindow", "AUTO"))
        self.fix_x_axis.setText(_translate("mainwindow", "FIX"))
        self.w_x_axis_label.setText(_translate("mainwindow", "X Axis"))
        self.w_auto_x_axis.setText(_translate("mainwindow", "AUTO"))
        self.w_fix_x_axis.setText(_translate("mainwindow", "FIX"))
        self.w_auto_y_axis.setText(_translate("mainwindow", "AUTO"))
        self.w_fix_y_axis.setText(_translate("mainwindow", "FIX"))
        self.label_7.setText(_translate("mainwindow", "Y Axis"))
        self.a3_label.setText(_translate("mainwindow", "a3"))
        self.a2_label.setText(_translate("mainwindow", "a2"))
        self.a1_label.setText(_translate("mainwindow", "a1"))
        self.a0_label.setText(_translate("mainwindow", "a0"))
        self.e3_label.setText(_translate("mainwindow", "E"))
        self.e2_label.setText(_translate("mainwindow", "E"))
        self.e1_label.setText(_translate("mainwindow", "E"))
        self.e0_label.setText(_translate("mainwindow", "E"))
        self.w_enter_button.setText(_translate("mainwindow", "Pixel to Lambda"))
        self.max_shutter_label.setText(_translate("mainwindow", "Max: "+str(st_max)+"\u03BCs"))
        self.max_anologgain_label.setText(_translate("mainwindow", "Max: "+str(ag_max)))
        self.max_digitalgain_label.setText(_translate("mainwindow", "Not Functioning"))
        self.auto_roi_label.setText(_translate("mainwindow", "ROI Scan"))
        self.auto_roi.setText(_translate("mainwindow", "Auto"))
        self.manual_roi.setText(_translate("mainwindow", "Manual"))
        self.auto_scaling_label.setText(_translate("mainwindow", "Auto Scaling"))
        self.auto_scaling.setText(_translate("mainwindow", "START"))
        self.I_max_label.setText(_translate("mainwindow", "Intensity Max"))
        self.I_max_label1.setText(_translate("mainwindow", "Max : 255"))
        self.I_thr_percentage_label.setText(_translate("mainwindow", "Thershold (%)"))
        self.I_thr_percentage_label1.setText(_translate("mainwindow", "TextLabel"))
        self.I_thr_tolerance_label.setText(_translate("mainwindow", "Thr tolerance"))
        self.I_thr_tolerance_label1.setText(_translate("mainwindow", "TextLabel"))
        self.numberof_scan_label.setText(_translate("mainwindow", "Num of scan"))
        self.numberof_scan_label1.setText(_translate("mainwindow", "TextLabel"))
        self.cameraspec_label.setText(_translate("mainwindow", "Sensor Specification"))
        self.cameraname_label.setText(_translate("mainwindow", "Model : OV9281"))
        self.camerawidth_label.setText(_translate("mainwindow", "IMG Width : 1280 Pixels"))
        self.cameraheight_label.setText(_translate("mainwindow", "IMG Height : 800 Pixels"))
        self.camerapixelsize_label.setText(_translate("mainwindow", "Pixel Size : 3 \u03BCm x 3 \u03BCm"))
        self.sg_filter_checkbox.setText(_translate("mainwindow", "SG Filter"))
        self.window_length_label.setText(_translate("mainwindow", "Data Point"))
        self.polyorder_label.setText(_translate("mainwindow", "Poly Order"))
        self.changedefault_label.setText(_translate("mainwindow", "Save As Default :"))
        self.roi_default_checkbox.setText(_translate("mainwindow", "ROI"))
        self.wavelength_parameter_checkbox.setText(_translate("mainwindow", "Wavelength Parameter"))
        self.cahnge_btn.setText(_translate("mainwindow", "Save"))
        self.w_parameter_label.setText(_translate("mainwindow", "Wavelength Calculation Parameters"))
        self.save_label.setText(_translate("mainwindow", "Save Function"))
        self.save_rd_data_checkbox.setText(_translate("mainwindow", "Raw Data"))
        self.save_sg_data_checkbox.setText(_translate("mainwindow", "SG Data"))
        self.save_file_label.setText(_translate("mainwindow", "Save File Name"))
        self.browse_file_label.setText(_translate("mainwindow", "Browse Path"))
        self.browse_save_button.setText(_translate("mainwindow", "Browse"))
        self.save_function_button.setText(_translate("mainwindow", "Save"))
        self.actionCalculate_wavelength.setText(_translate("mainwindow", "Calculate Wavelength Parameter"))
        self.transmission_mode.setText(_translate("mainwindow", "Transmission Mode"))
        self.pixel_graph.setBackground('w')
        self.pixel_graph.setLabel('left', 'Intensity')
        self.pixel_graph.setLabel('bottom', 'Pixel')
        
        self.wavelength_graph.setBackground('w')
        self.wavelength_graph.setLabel('left', 'Intensity')
        self.wavelength_graph.setLabel('bottom', 'Wavelength')
        
        grey = QtGui.QPixmap(300,200)
        grey.fill(QtGui.QColor('darkgrey'))
        self.image_frame.setPixmap(grey)
        
        self.shutter_edit.setText(shutter)
        self.anologgain_edit.setText(anolog_gain)
        self.digitalgain_edit.setText(digital_gain)
        self.x0.setText(x)
        self.y0.setText(y)
        self.x1.setText(deltax)
        self.y1.setText(deltay)
        self.Yaxis_min.setText(y_axis_min)
        self.Yaxis_max.setText(y_axis_max)
        self.Xaxis_min.setText(x_axis_min)
        self.Xaxis_max.setText(x_axis_max)
        self.W_Yaxis_min.setText(y_axis_min)
        self.W_Yaxis_max.setText(y_axis_max)
        self.W_Xaxis_min.setText(x_axis_min)
        self.W_Xaxis_max.setText(x_axis_max)
        
        self.a3.setText(a3)
        self.a2.setText(a2)
        self.a1.setText(a1)
        self.a0.setText(a0)
        self.e3.setText(e3)
        self.e2.setText(e2)
        self.e1.setText(e1)
        self.e0.setText(e0)
        
        self.I_max_edit.setText(I_max)
        self.I_thr_percentage_edit.setText(I_thr_percentage)
        self.I_thr_tolerance_edit.setText(I_thr_tolerance)
        
        I_max = int(ui.I_max_edit.text())
        I_thr_percentage = int(ui.I_thr_percentage_edit.text())
        I_thr_tolerance = int(ui.I_thr_tolerance_edit.text())
        I_thr = I_max * I_thr_percentage/100
        I_thr_top = I_thr + I_thr_tolerance
        I_thr_bottom = I_thr - I_thr_tolerance
        self.I_thr_tolerance_label1.setText(_translate("mainwindow", str(I_thr_top) + ' ~ ' + str(I_thr_bottom)))
        self.I_thr_percentage_label1.setText(_translate("mainwindow", str(I_thr)))
        
        self.numberof_scan_edit.setText(num_scan)
        self.numberof_scan_label1.setText(_translate("mainwindow", str(((float(shutter) / 1000) * float(num_scan) + 500 * float(num_scan)) / 1000 ) + ' seconds'))
        
        self.window_length_edit.setText(w_length)
        self.polyorder_edit.setText(poly_order)
        # 設定輸入格式
        self.shutter_edit.setValidator(QtGui.QIntValidator())
        self.anologgain_edit.setValidator(QtGui.QDoubleValidator())
        self.digitalgain_edit.setValidator(QtGui.QDoubleValidator())
        self.x0.setValidator(QtGui.QIntValidator())
        self.y0.setValidator(QtGui.QIntValidator())
        self.x1.setValidator(QtGui.QIntValidator())
        self.y1.setValidator(QtGui.QIntValidator())
        self.Xaxis_min.setValidator(QtGui.QIntValidator())
        self.Xaxis_max.setValidator(QtGui.QIntValidator())
        self.Yaxis_min.setValidator(QtGui.QIntValidator())
        self.Yaxis_max.setValidator(QtGui.QIntValidator())
        self.a0.setValidator(QtGui.QDoubleValidator())
        self.a1.setValidator(QtGui.QDoubleValidator())
        self.a2.setValidator(QtGui.QDoubleValidator())
        self.a3.setValidator(QtGui.QDoubleValidator())
        self.e0.setValidator(QtGui.QIntValidator())
        self.e1.setValidator(QtGui.QIntValidator())
        self.e2.setValidator(QtGui.QIntValidator())
        self.e3.setValidator(QtGui.QIntValidator())
        self.I_max_edit.setValidator(QtGui.QIntValidator())
        self.I_thr_percentage_edit.setValidator(QtGui.QIntValidator())
        self.I_thr_tolerance_edit.setValidator(QtGui.QIntValidator())
        self.numberof_scan_edit.setValidator(QtGui.QIntValidator())
        self.window_length_edit.setValidator(QtGui.QIntValidator())
        self.polyorder_edit.setValidator(QtGui.QIntValidator())
        
        self.Xaxis_min.setEnabled(False)
        self.Xaxis_max.setEnabled(False)
        self.Yaxis_min.setEnabled(False)
        self.Yaxis_max.setEnabled(False)
        self.W_Xaxis_min.setEnabled(False)
        self.W_Xaxis_max.setEnabled(False)
        self.W_Yaxis_min.setEnabled(False)
        self.W_Yaxis_max.setEnabled(False)
        self.save_file_edit.setEnabled(False)
        self.browse_file_edit.setEnabled(False)
        self.save_function_button.setEnabled(False)
        self.browse_save_button.setEnabled(False)
        
        self.auto_x_axis.setChecked(True)
        self.auto_y_axis.setChecked(True)
        self.w_auto_x_axis.setChecked(True)
        self.w_auto_y_axis.setChecked(True)
        self.manual_roi.setChecked(True)
    # 執行 thread_1
    def start_clicked(self):  # num of scan
        global mode, flag
        _translate = QtCore.QCoreApplication.translate

        if ui.continue_checkbox.isChecked() == True:
            if flag == 0:
                flag = 1
                self.start.setText(_translate("mainwindow", "STOP"))
            elif flag == 1:
                flag = 0
                self.start.setText(_translate("mainwindow", "START"))
                return
        else:
            flag = 0
            mode = 10
            
        thread1 = threading.Thread(target = thread_1)
        thread1.daemon = True
        thread1.start()
        # 調整Pixel graph 座標範圍
    def y_axis_clicked(self):
        _translate = QtCore.QCoreApplication.translate
        
        if self.fix_y_axis.isChecked(): 
            yaxis_min = self.Yaxis_min.text()
            yaxis_max = self.Yaxis_max.text()
            self.pixel_graph.setYRange(int(yaxis_min), int(yaxis_max), padding=0)
            self.Yaxis_min.setEnabled(True)
            self.Yaxis_max.setEnabled(True)
            
        elif self.auto_y_axis.isChecked():
            self.pixel_graph.enableAutoRange(axis='y')
            self.Yaxis_min.setEnabled(False)
            self.Yaxis_max.setEnabled(False)
            
    def x_axis_clicked(self):
        _translate = QtCore.QCoreApplication.translate
        
        if self.fix_x_axis.isChecked():
            xaxis_min = self.Xaxis_min.text()
            xaxis_max = self.Xaxis_max.text()
            self.pixel_graph.setXRange(int(xaxis_min), int(xaxis_max), padding=0)
            self.Xaxis_min.setEnabled(True)
            self.Xaxis_max.setEnabled(True)
        elif self.auto_x_axis.isChecked():
            self.pixel_graph.enableAutoRange(axis='x')
            self.Xaxis_min.setEnabled(False)
            self.Xaxis_max.setEnabled(False)

    def y_axis_fix(self):
        yaxis_min = self.Yaxis_min.text()
        yaxis_max = self.Yaxis_max.text()
        self.pixel_graph.setYRange(int(yaxis_min), int(yaxis_max), padding=0)
        
    def x_axis_fix(self):
        xaxis_min = self.Xaxis_min.text()
        xaxis_max = self.Xaxis_max.text()
        self.pixel_graph.setXRange(int(xaxis_min), int(xaxis_max), padding=0)
        
    
    # 調整 Wavelength graph 座標範圍
    def w_y_axis_clicked(self):
        _translate = QtCore.QCoreApplication.translate
        
        if self.w_fix_y_axis.isChecked(): 
            yaxis_min = self.W_Yaxis_min.text()
            yaxis_max = self.W_Yaxis_max.text()
            
            self.wavelength_graph.setYRange(int(yaxis_min), int(yaxis_max), padding=0)
            self.W_Yaxis_min.setEnabled(True)
            self.W_Yaxis_max.setEnabled(True)
        elif self.w_auto_y_axis.isChecked():
            self.wavelength_graph.enableAutoRange(axis='y')
            self.W_Yaxis_min.setEnabled(False)
            self.W_Yaxis_max.setEnabled(False)
        
    def w_x_axis_clicked(self):
        _translate = QtCore.QCoreApplication.translate
        
        if self.w_fix_x_axis.isChecked(): 
            xaxis_min = self.W_Xaxis_min.text()
            xaxis_max = self.W_Xaxis_max.text()
            self.wavelength_graph.setXRange(int(xaxis_min), int(xaxis_max), padding=0)
            self.W_Xaxis_min.setEnabled(True)
            self.W_Xaxis_max.setEnabled(True)
        elif self.w_auto_x_axis.isChecked():
            self.wavelength_graph.enableAutoRange(axis='x')
            self.W_Xaxis_min.setEnabled(False)
            self.W_Xaxis_max.setEnabled(False)

    def w_y_axis_fix(self):
        yaxis_min = self.W_Yaxis_min.text()
        yaxis_max = self.W_Yaxis_max.text()
        self.wavelength_graph.setYRange(int(yaxis_min), int(yaxis_max), padding=0)
        
    def w_x_axis_fix(self):
        xaxis_min = self.W_Xaxis_min.text()
        xaxis_max = self.W_Xaxis_max.text()
        self.wavelength_graph.setXRange(int(xaxis_min), int(xaxis_max), padding=0)

    # 執行 thread_2
    def auto_scaling_clicked(self):
        global auto_mode,window_num
        
        auto_mode = 10
        window_num = 1
        thread2 = threading.Thread(target = thread_2)
        thread2.daemon = True
        thread2.start()
    # 執行 auto_roi 並執行thread_1
    def auto_roi_clicked(self):
        global roi_mode, mode
        _translate = QtCore.QCoreApplication.translate
        roi_mode=0
        mode = 10
        self.x0.setEnabled(False)
        self.y0.setEnabled(False)
        self.x1.setEnabled(False)
        self.manual_roi.setChecked(False)
        
        thread1 = threading.Thread(target = thread_1)
        thread1.daemon = True
        thread1.start()
    # 手動設定 roi 範圍
    def manual_roi_clicked(self):
        global roi_mode, mode
        _translate = QtCore.QCoreApplication.translate
        roi_mode=1
        mode = 10
        self.x0.setEnabled(True)
        self.y0.setEnabled(True)
        self.x1.setEnabled(True)
        self.auto_roi.setChecked(False)
    # 呼叫 second window
    def w_cal_button_clicked(self):
        c_ui.c_graph.clear()
        x = np.arange(1, len(ncolmean)+1)
        if self.sg_filter_checkbox.isChecked():
            #savgol_filter(data, window length, polyorder)
            y = signal.savgol_filter(ncolmean, int(self.window_length_edit.text()), int(self.polyorder_edit.text()))
        else:
            y = ncolmean
        c_ui.c_graph.plot(x, y, pen=pg.mkPen('k'))
        secondwindow.show()
    # 波長轉換
    def w_enter_button_clicked(self):
        check = wavelength_convert()
        if check!=1:
            raise Exception
        check = self.draw_wavelength_graph_signal()
        if check!=1:
            raise Exception
    # save as default btn
    def change_btn_clicked(self):
        self.statusbar.showMessage("Changing Default")
        
        if self.roi_default_checkbox.isChecked() == True or self.wavelength_parameter_checkbox.isChecked() == True:
            if self.roi_default_checkbox.isChecked() == True:
                config['default']['x'] = self.x0.text()
                config['default']['y'] = self.y0.text()
                config['default']['deltax'] = self.x1.text()
                config['default']['deltay'] = self.y1.text()
            
            if self.wavelength_parameter_checkbox.isChecked() == True:
                config['wavelength_calibration']['a3'] = self.a3.text()
                config['wavelength_calibration']['a2'] = self.a2.text()
                config['wavelength_calibration']['a1'] = self.a1.text()
                config['wavelength_calibration']['a0'] = self.a0.text()
                config['wavelength_calibration']['e3'] = self.e3.text()
                config['wavelength_calibration']['e2'] = self.e2.text()
                config['wavelength_calibration']['e1'] = self.e1.text()
                config['wavelength_calibration']['e0'] = self.e0.text()
            
            with open('config.ini','w') as configfile:
                config.write(configfile)
                
            self.statusbar.showMessage("Default change complete")
        else:
            self.statusbar.showMessage("Please tick 1 or both checkbox to change default")
    # browse_function_button
    def browse_function_button_clicked(self):
        filename = QtWidgets.QFileDialog.getExistingDirectory(None, 'Save Path', '')
        self.browse_file_edit.setText(filename)
        
    def save_function_button_clicked(self):
        try:
            self.statusbar.showMessage("Saving")
            
            path = self.save_file_edit.text()
            dic = self.browse_file_edit.text()
            if path == "":
                path = time.strftime("%Y%m%d_%H%M%S")
            if dic != "":
                dic += "/" 
                
            if self.save_rd_data_checkbox.isChecked():
                path_raw = dic + path + "_raw.txt"
                s = ncolmean
                check = self.helper_save_funtion(path_raw, s)
                if check != 1:
                    raise Exception
                    
            if self.save_sg_data_checkbox.isChecked():
                path_sg = dic + path + "_sg.txt"
                s = signal.savgol_filter(ncolmean, int(self.window_length_edit.text()), int(self.polyorder_edit.text()))
                check = self.helper_save_funtion(path_sg, s)
                if check != 1:
                    raise Exception
                    
            self.statusbar.showMessage("Save Complete")
            
        except Exception as e:
            print('error:{}'.format(e))
            self.statusbar.showMessage("Save Error")            
    
    def helper_save_funtion(self, path, data):
        try:
            f = open(path, 'w')
            for i in data:
                f.write(str(i) + "\n")
            f.close()
            
            return 1
        except Exception as e:
            print('error:{}'.format(e))
            return 0
            
    def continue_checkbox_check(self):
        global flag
        _translate = QtCore.QCoreApplication.translate
        
        if ui.continue_checkbox.isChecked() == False:
            flag = 0
            self.start.setText(_translate("mainwindow", "START"))
    
    def sg_filter_checkbox_check(self):
        self.draw_both_graph_signal()
        if secondwindow.isVisible():
            c_ui.c_graph.clear()
            x = np.arange(1, len(ncolmean)+1)
            if self.sg_filter_checkbox.isChecked():
                #savgol_filter(data, window length, polyorder)
                y = signal.savgol_filter(ncolmean, int(self.window_length_edit.text()), int(self.polyorder_edit.text()))
            else:
                y = ncolmean
            c_ui.c_graph.plot(x, y, pen=pg.mkPen('k'))
            
            if c_draw_wgraph == 1:
                check = c_ui.w_draw_wgraph()
                if check == 0:
                    raise Exception
    
    def save_data_check(self):
        if self.save_rd_data_checkbox.isChecked() or self.save_sg_data_checkbox.isChecked():
            self.save_file_edit.setEnabled(True)
            self.browse_file_edit.setEnabled(True)
            self.save_function_button.setEnabled(True)
            self.browse_save_button.setEnabled(True)
        elif self.save_rd_data_checkbox.isChecked() == False and self.save_sg_data_checkbox.isChecked() == False :
            self.save_file_edit.setEnabled(False)
            self.save_function_button.setEnabled(False)
            self.browse_file_edit.setEnabled(False)
            self.browse_save_button.setEnabled(False)
            
    # roi 調整
    def roi_change(self):
        check = crop_image()
        if check != 1:
            raise Exception
        check = number_ofscan()
        if check != 1:
            raise Exception
        check = cal_number_ofscan()
        if check != 1:
            raise Exception
        check = self.draw_spectrum_graph_signal()
        if check != 1:
            raise Exception
        check = self.update_image_signal()
        if check != 1:
            raise Exception
        check = wavelength_convert()
        if check != 1:
            raise Exception
        check = self.draw_wavelength_graph_signal()
        if check != 1:
            raise Exception
        print("ROI DONE")
    
    # auto_scaling_paremeter_change
    def auto_scaling_paremeter_change(self):
        _translate = QtCore.QCoreApplication.translate
        
        I_max = int(self.I_max_edit.text())
        
        if I_max > 255:
            self.I_max_edit.setText("255")
        I_thr_percentage = int(self.I_thr_percentage_edit.text())
        I_thr_tolerance = int(self.I_thr_tolerance_edit.text())
        I_thr = I_max * I_thr_percentage/100
        I_thr_top = I_thr + I_thr_tolerance
        I_thr_bottom = I_thr - I_thr_tolerance
        self.I_thr_tolerance_label1.setText(_translate("mainwindow", str(I_thr_top) + '~' + str(I_thr_bottom)))
        self.I_thr_percentage_label1.setText(_translate("mainwindow", str(I_thr)))

    # 處理照片時間
    def scan_number_change(self):
        global num_scan
        
        num_scan = self.numberof_scan_edit.text()
        
        _translate = QtCore.QCoreApplication.translate
        self.numberof_scan_label1.setText(_translate("mainwindow", str(((float(shutter) / 1000) * float(num_scan) + 500 * float(num_scan)) / 1000 ) + ' seconds'))
    
    def shutter_change(self):
        global shutter
        
        shutter = self.shutter_edit.text()
        _translate = QtCore.QCoreApplication.translate
        self.numberof_scan_label1.setText(_translate("mainwindow", str(((float(shutter) / 1000) * float(num_scan) + 500 * float(num_scan)) / 1000 ) + ' seconds'))
    
    def sg_change(self):
        self.draw_both_graph_signal()
    # auto roi scan
    def roi_scan(self):
        global max_value, new_y1
        
        try:
            deltay = int(self.y1.text())
            
            img = cv2.imread("./ttest/test.{}".format(self.format_box.currentText().lower()), cv2.IMREAD_GRAYSCALE)
            a1, a2 = np.where(img == np.amax(img))
            new_y1 = a1[0]-deltay/2
            if new_y1 <= 0:
                new_y1 = 0
            signalComm.new_y0.emit()
            
            return 1                             # 都扣完後的ㄆ
        except Exception as e:
            print('error:{}'.format(e))
            return 0
    # 畫 roi 範圍
    def draw_roi(self, img):
        x0 = int(self.x0.text())
        y0 = int(self.y0.text())
        deltax = int(self.x1.text())
        deltay = int(self.y1.text())
        x1 = x0 + deltax
        y1 = y0 + deltay
        
        roi_start_point = (x0, y0)
        roi_end_point = (x1, y1)
        roi_color = (255, 0 , 0) #GBR
        thickness = 3
        
        img1 = cv2.rectangle(img, roi_start_point, roi_end_point, roi_color, thickness)
        return img1
    # 畫 pixel graph
    def update_data(self):
        try:
            self.pixel_graph.clear()
            x = np.arange(1,len(ncolmean)+1)
            if self.sg_filter_checkbox.isChecked():
                #savgol_filter(data, window length, polyorder)
                y = signal.savgol_filter(ncolmean, int(self.window_length_edit.text()), int(self.polyorder_edit.text()))
            else:
                y = ncolmean
            self.pixel_graph.plot(x, y, pen=pg.mkPen('k'))  # k = black
            
            return 1
        except Exception as e:
            print('error:{}'.format(e))
            return 0    
    # 畫 wavelength graph
    def update_wdata(self):
        try:
            self.wavelength_graph.clear()
            x = wdata
            if self.sg_filter_checkbox.isChecked():
                y = signal.savgol_filter(ncolmean, int(self.window_length_edit.text()), int(self.polyorder_edit.text()))
            else:
                y = ncolmean
            self.wavelength_graph.plot(x, y, pen=pg.mkPen('k')) # k = black
            
            return 1
        except Exception as e:
            print('error:{}'.format(e))
            return 0    
    
    def update_image(self):
        try:
            imgformat = self.format_box.currentText().lower()
            imgpath = "./ttest/test.{}".format(imgformat)
            img = cv2.imread(imgpath)
            img1 = self.draw_roi(img)
            
            h, w, ch= img1.shape
            bytes_per_line = 3 * w
            convert_QT_image = QtGui.QImage(img1.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888).rgbSwapped()
            p = convert_QT_image.scaled(self.image_frame.frameGeometry().width(), self.image_frame.frameGeometry().height(), QtCore.Qt.KeepAspectRatio)
            self.image_frame.setPixmap(QtGui.QPixmap.fromImage(p))
            
            return 1
        except Exception as e:
            print('error:{}'.format(e))
            return 0
    # autoscaling update_st
    def update_st(self):
        try:
            if window_num == 1:
                self.shutter_edit.setText(str(goal_st))
            else:
                t_ui.shutter_lineEdit.setText(str(goal_st))
            return 1
        except Exception as e:
            print('error:{}'.format(e))
            return 0
    
    def update_y0(self):
        try:
            self.y0.setText(str(int(new_y0)))
            return 1
        except Exception as e:
            print('error:{}'.format(e))
            return 0
                                
    def draw_spectrum_graph_signal(self):
        try:
            signalComm.new_data.emit()
            return 1
        except Exception as e:
            print('error:{}'.format(e))
            return 0    
            
    def draw_wavelength_graph_signal(self):
        try:
            signalComm.new_wdata.emit()
            return 1
        except Exception as e:
            print('error:{}'.format(e))
            return 0    
    
    def draw_both_graph_signal(self):
        try:
            signalComm.new_data.emit()
            signalComm.new_wdata.emit()
            return 1
        except Exception as e:
            print('error:{}'.format(e))
            return 0
    
    def update_shutter_signal(self):
        try:
            signalComm.new_goal_st.emit()
            return 1
        except Exception as e:
            print('error:{}'.format(e))
            return 0
    
    def update_image_signal(self):
        try:
            signalComm.new_image.emit()
            return 1
        except Exception as e:
            print('error:{}'.format(e))
            return 0
    
    def update_y0_signal(self):
        try:
            signalComm.new_y0.emit()
            return 1
        except Exception as e:
            print('error:{}'.format(e))
            return 0
    def transmission_window_show(self):
        try:
            Transmission_window.show()
            t_ui.refresh_com()
        except Exception as e:
            print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e))
            return 0  
    # second window
class Ui_w_calibration(object):
    def setupUi(self, w_calibration):
        w_calibration.setObjectName("w_calibration")
        w_calibration.setEnabled(True)
        w_calibration.resize(630, 630)
        
        self.fill_in_table = QtWidgets.QTableView(w_calibration)
        self.fill_in_table.setGeometry(QtCore.QRect(10, 90, 190, 315))
        self.fill_in_table.setObjectName("fill_in_table")
        self.label = QtWidgets.QLabel(w_calibration)
        self.label.setGeometry(QtCore.QRect(20, 100, 100, 16))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(w_calibration)
        self.label_2.setGeometry(QtCore.QRect(20, 120, 100, 16))
        self.label_2.setObjectName("label_2")
        self.label_3 = QtWidgets.QLabel(w_calibration)
        self.label_3.setGeometry(QtCore.QRect(20, 145, 100, 16))
        self.label_3.setObjectName("label_3")
        self.label_4 = QtWidgets.QLabel(w_calibration)
        self.label_4.setGeometry(QtCore.QRect(20, 170, 100, 16))
        self.label_4.setObjectName("label_4")
        self.label_5 = QtWidgets.QLabel(w_calibration)
        self.label_5.setGeometry(QtCore.QRect(20, 195, 100, 16))
        self.label_5.setObjectName("label_5")
        self.label_6 = QtWidgets.QLabel(w_calibration)
        self.label_6.setGeometry(QtCore.QRect(20, 220, 100, 16))
        self.label_6.setObjectName("label_6")
        self.label_7 = QtWidgets.QLabel(w_calibration)
        self.label_7.setGeometry(QtCore.QRect(20, 245, 100, 16))
        self.label_7.setObjectName("label_7")
        self.label_8 = QtWidgets.QLabel(w_calibration)
        self.label_8.setGeometry(QtCore.QRect(20, 270, 100, 16))
        self.label_8.setObjectName("label_8")
        self.label_9 = QtWidgets.QLabel(w_calibration)
        self.label_9.setGeometry(QtCore.QRect(70, 100, 100, 16))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_9.setFont(font)
        self.label_9.setObjectName("label_9")
        self.label_10 = QtWidgets.QLabel(w_calibration)
        self.label_10.setGeometry(QtCore.QRect(20, 295, 100, 16))
        self.label_10.setObjectName("label_10")
        self.label_11 = QtWidgets.QLabel(w_calibration)
        self.label_11.setGeometry(QtCore.QRect(20, 320, 100, 16))
        self.label_11.setObjectName("label_11")
        self.label_12 = QtWidgets.QLabel(w_calibration)
        self.label_12.setGeometry(QtCore.QRect(20, 345, 100, 16))
        self.label_12.setObjectName("label_12")
        
        self.lambda1 = QtWidgets.QLineEdit(w_calibration)
        self.lambda1.setGeometry(QtCore.QRect(60, 120, 70, 20))
        self.lambda1.setObjectName("lambda1")
        self.lambda2 = QtWidgets.QLineEdit(w_calibration)
        self.lambda2.setGeometry(QtCore.QRect(60, 142, 70, 20))
        self.lambda2.setObjectName("lambda2")
        self.lambda3 = QtWidgets.QLineEdit(w_calibration)
        self.lambda3.setGeometry(QtCore.QRect(60, 170, 70, 20))
        self.lambda3.setObjectName("lambda3")
        self.lambda4 = QtWidgets.QLineEdit(w_calibration)
        self.lambda4.setGeometry(QtCore.QRect(60, 195, 70, 20))
        self.lambda4.setObjectName("lambda4")
        self.lambda5 = QtWidgets.QLineEdit(w_calibration)
        self.lambda5.setGeometry(QtCore.QRect(60, 220, 70, 20))
        self.lambda5.setObjectName("lambda5")
        self.lambda6 = QtWidgets.QLineEdit(w_calibration)
        self.lambda6.setGeometry(QtCore.QRect(60, 245, 70, 20))
        self.lambda6.setObjectName("lambda6")
        self.lambda7 = QtWidgets.QLineEdit(w_calibration)
        self.lambda7.setGeometry(QtCore.QRect(60, 270, 70, 20))
        self.lambda7.setObjectName("lambda7")
        self.lambda8 = QtWidgets.QLineEdit(w_calibration)
        self.lambda8.setGeometry(QtCore.QRect(60, 295, 70, 20))
        self.lambda8.setObjectName("lambda8")
        self.lambda9 = QtWidgets.QLineEdit(w_calibration)
        self.lambda9.setGeometry(QtCore.QRect(60, 320, 70, 20))
        self.lambda9.setObjectName("lambda9")
        self.lambda10 = QtWidgets.QLineEdit(w_calibration)
        self.lambda10.setGeometry(QtCore.QRect(60, 345, 70, 20))
        self.lambda10.setObjectName("lambda10")
        
        self.pixel1 = QtWidgets.QLineEdit(w_calibration)
        self.pixel1.setGeometry(QtCore.QRect(140, 120, 50, 20))
        self.pixel1.setObjectName("pixel1")
        self.pixel2 = QtWidgets.QLineEdit(w_calibration)
        self.pixel2.setGeometry(QtCore.QRect(140, 145, 50, 20))
        self.pixel2.setObjectName("pixel2")
        self.pixel3 = QtWidgets.QLineEdit(w_calibration)
        self.pixel3.setGeometry(QtCore.QRect(140, 170, 50, 20))
        self.pixel3.setObjectName("pixel3")
        self.pixel4 = QtWidgets.QLineEdit(w_calibration)
        self.pixel4.setGeometry(QtCore.QRect(140, 195, 50, 20))
        self.pixel4.setObjectName("pixel4")
        self.pixel5 = QtWidgets.QLineEdit(w_calibration)
        self.pixel5.setGeometry(QtCore.QRect(140, 220, 50, 20))
        self.pixel5.setObjectName("pixel5")
        self.pixel6 = QtWidgets.QLineEdit(w_calibration)
        self.pixel6.setGeometry(QtCore.QRect(140, 245, 50, 20))
        self.pixel6.setObjectName("pixel6")
        self.pixel7 = QtWidgets.QLineEdit(w_calibration)
        self.pixel7.setGeometry(QtCore.QRect(140, 270, 50, 20))
        self.pixel7.setObjectName("pixel7")
        self.pixel8 = QtWidgets.QLineEdit(w_calibration)
        self.pixel8.setGeometry(QtCore.QRect(140, 295, 50, 20))
        self.pixel8.setObjectName("pixel8")
        self.pixel9 = QtWidgets.QLineEdit(w_calibration)
        self.pixel9.setGeometry(QtCore.QRect(140, 320, 50, 20))
        self.pixel9.setObjectName("pixel9")
        self.pixel10 = QtWidgets.QLineEdit(w_calibration)
        self.pixel10.setGeometry(QtCore.QRect(140, 345, 50, 20))
        self.pixel10.setObjectName("pixel10")
        
        self.CalButton = QtWidgets.QPushButton(w_calibration)
        self.CalButton.setGeometry(QtCore.QRect(104, 370, 90, 30))
        self.CalButton.setObjectName("CalButton")
        
        self.tableView = QtWidgets.QTableView(w_calibration)
        self.tableView.setGeometry(QtCore.QRect(10, 410, 190, 100))
        self.tableView.setObjectName("tableView")
        self.label_17 = QtWidgets.QLabel(w_calibration)
        self.label_17.setGeometry(QtCore.QRect(20, 415, 20, 15))
        self.label_17.setObjectName("label_17")
        self.label_18 = QtWidgets.QLabel(w_calibration)
        self.label_18.setGeometry(QtCore.QRect(20, 440, 20, 15))
        self.label_18.setObjectName("label_18")
        self.label_19 = QtWidgets.QLabel(w_calibration)
        self.label_19.setGeometry(QtCore.QRect(20, 465, 20, 15))
        self.label_19.setObjectName("label_19")
        self.label_20 = QtWidgets.QLabel(w_calibration)
        self.label_20.setGeometry(QtCore.QRect(20, 490, 20, 15))
        self.label_20.setObjectName("label_20")
        self.a3_label = QtWidgets.QLabel(w_calibration)
        self.a3_label.setGeometry(QtCore.QRect(50, 415, 100, 15))
        self.a3_label.setObjectName("a3_label")
        self.a0_label = QtWidgets.QLabel(w_calibration)
        self.a0_label.setGeometry(QtCore.QRect(50, 490, 100, 15))
        self.a0_label.setObjectName("a0_label")
        self.a1_label = QtWidgets.QLabel(w_calibration)
        self.a1_label.setGeometry(QtCore.QRect(50, 465, 100, 15))
        self.a1_label.setObjectName("a1_label")
        self.a2_label = QtWidgets.QLabel(w_calibration)
        self.a2_label.setGeometry(QtCore.QRect(50, 440, 100, 15))
        self.a2_label.setObjectName("a2_label")
        
        self.c_graph = pg.PlotWidget(w_calibration)
        self.c_graph.setGeometry(QtCore.QRect(220, 10, 400, 300))
        self.c_wavelength_graph = pg.PlotWidget(w_calibration)
        self.c_wavelength_graph.setGeometry(QtCore.QRect(220, 320, 400, 300))
        
        self.pixel_label = QtWidgets.QLabel(w_calibration)
        self.pixel_label.setGeometry(QtCore.QRect(140, 100, 100, 16))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.pixel_label.setFont(font)
        self.pixel_label.setObjectName("pixel_label")
        
        self.tableView_2 = QtWidgets.QTableView(w_calibration)
        self.tableView_2.setGeometry(QtCore.QRect(10, 10, 190, 71))
        self.tableView_2.setObjectName("tableView_2")
        self.ar_autopeak_checkbox = QtWidgets.QCheckBox(w_calibration)
        self.ar_autopeak_checkbox.setGeometry(QtCore.QRect(20, 50, 140, 16))
        self.ar_autopeak_checkbox.setObjectName("ar_autopeak_checkbox")
        self.autopeak_label = QtWidgets.QLabel(w_calibration)
        self.autopeak_label.setGeometry(QtCore.QRect(20, 20, 200, 16))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.autopeak_label.setFont(font)
        self.autopeak_label.setObjectName("autopeak_label")
        
        self.tableView_3 = QtWidgets.QTableView(w_calibration)
        self.tableView_3.setGeometry(QtCore.QRect(10, 520, 190, 100))
        self.tableView_3.setObjectName("tableView_3")
        self.model_comboBox = QtWidgets.QComboBox(w_calibration)
        self.model_comboBox.setGeometry(QtCore.QRect(70, 550, 121, 22))
        self.model_comboBox.setObjectName("model_comboBox")
        self.model_comboBox.addItem("")
        self.model_label = QtWidgets.QLabel(w_calibration)
        self.model_label.setGeometry(QtCore.QRect(20, 555, 100, 16))
        self.model_label.setObjectName("model_label")
        self.model_label_2 = QtWidgets.QLabel(w_calibration)
        self.model_label_2.setGeometry(QtCore.QRect(20, 530, 150, 16))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.model_label_2.setFont(font)
        self.model_label_2.setObjectName("model_label_2")
        self.ar_autofindpeak_btn = QtWidgets.QPushButton(w_calibration)
        self.ar_autofindpeak_btn.setGeometry(QtCore.QRect(20, 580, 90, 30))
        self.ar_autofindpeak_btn.setObjectName("ar_autofindpeak_btn")
        
        self.retranslateUi(w_calibration)
        QtCore.QMetaObject.connectSlotsByName(w_calibration)
        
        self.CalButton.clicked.connect(self.w_cal_button_clicked)
        self.ar_autofindpeak_btn.clicked.connect(self.ar_autofindpeak_btn_clicked)
        
        self.ar_autopeak_checkbox.toggled.connect(self.ar_autopeak_checkbox_check)
        
        signalComm.new_pixel.connect(self.update_pixel)
        
    def retranslateUi(self, w_calibration):
        _translate = QtCore.QCoreApplication.translate
        w_calibration.setWindowTitle(_translate("w_calibration", "Wavelength Calibration "+version))
        self.label.setText(_translate("w_calibration", "NO."))
        self.label_2.setText(_translate("w_calibration", "1"))
        self.label_3.setText(_translate("w_calibration", "2"))
        self.label_4.setText(_translate("w_calibration", "3"))
        self.label_5.setText(_translate("w_calibration", "4"))
        self.label_6.setText(_translate("w_calibration", "5"))
        self.label_7.setText(_translate("w_calibration", "6"))
        self.label_8.setText(_translate("w_calibration", "7"))
        self.label_9.setText(_translate("w_calibration", "Lambda"))
        self.label_10.setText(_translate("w_calibration", "8"))
        self.label_11.setText(_translate("w_calibration", "9"))
        self.label_12.setText(_translate("w_calibration", "10"))
        self.CalButton.setText(_translate("w_calibration", "CALCULATE"))
        self.label_17.setText(_translate("w_calibration", "a3"))
        self.label_18.setText(_translate("w_calibration", "a2"))
        self.label_19.setText(_translate("w_calibration", "a1"))
        self.label_20.setText(_translate("w_calibration", "a0"))
        self.a3_label.setText(_translate("w_calibration", "---"))
        self.a0_label.setText(_translate("w_calibration", "---"))
        self.a1_label.setText(_translate("w_calibration", "---"))
        self.a2_label.setText(_translate("w_calibration", "---"))
        self.pixel_label.setText(_translate("w_calibration", "Pixel"))
        self.ar_autopeak_checkbox.setText(_translate("w_calibration", "Hg-Ar Peaks"))
        self.ar_autofindpeak_btn.setText(_translate("w_calibration", "AUTO FIND"))
        self.autopeak_label.setText(_translate("w_calibration", " Defaut Wavelengths"))
        self.model_label.setText(_translate("w_calibration", "Model"))
        self.model_label_2.setText(_translate("w_calibration", "Auto Find Peak"))
        
        self.lambda1.setText('0')
        self.lambda2.setText('0')
        self.lambda3.setText('0')
        self.lambda4.setText('0')
        self.lambda5.setText('0')
        self.lambda6.setText('0')
        self.lambda7.setText('0')
        self.lambda8.setText('0')
        self.lambda9.setText('0')
        self.lambda10.setText('0')
        
        self.pixel1.setText('0')
        self.pixel2.setText('0')
        self.pixel3.setText('0')
        self.pixel4.setText('0')
        self.pixel5.setText('0')
        self.pixel6.setText('0')
        self.pixel7.setText('0')
        self.pixel8.setText('0')
        self.pixel9.setText('0')
        self.pixel10.setText('0')
        
        self.lambda1.setValidator(QtGui.QDoubleValidator())
        self.lambda2.setValidator(QtGui.QDoubleValidator())
        self.lambda3.setValidator(QtGui.QDoubleValidator())
        self.lambda4.setValidator(QtGui.QDoubleValidator())
        self.lambda5.setValidator(QtGui.QDoubleValidator())
        self.lambda6.setValidator(QtGui.QDoubleValidator())
        self.lambda7.setValidator(QtGui.QDoubleValidator())
        self.lambda8.setValidator(QtGui.QDoubleValidator())
        self.lambda9.setValidator(QtGui.QDoubleValidator())
        self.lambda10.setValidator(QtGui.QDoubleValidator())
        
        self.pixel1.setValidator(QtGui.QDoubleValidator())
        self.pixel2.setValidator(QtGui.QDoubleValidator())
        self.pixel3.setValidator(QtGui.QDoubleValidator())
        self.pixel4.setValidator(QtGui.QDoubleValidator())
        self.pixel5.setValidator(QtGui.QDoubleValidator())
        self.pixel6.setValidator(QtGui.QDoubleValidator())
        self.pixel7.setValidator(QtGui.QDoubleValidator())
        self.pixel8.setValidator(QtGui.QDoubleValidator())
        self.pixel9.setValidator(QtGui.QDoubleValidator())
        self.pixel10.setValidator(QtGui.QDoubleValidator())
        
        self.c_graph.setBackground('w')
        self.c_graph.setLabel('left', 'Intensity')
        self.c_graph.setLabel('bottom', 'Pixel')
        
        self.c_wavelength_graph.setBackground('w')
        self.c_wavelength_graph.setLabel('left', 'Intensity')
        self.c_wavelength_graph.setLabel('bottom', 'Wavelength')
        
        self.ar_autofindpeak_btn.setEnabled(False)

    # 計算波長校正係數
    def w_cal_button_clicked(self):
        global c_draw_wgraph
        try:
            ui.statusbar.showMessage("Wavelength Equation Calculating")
            
            x1 = []
            y1 = []

            if (float(self.pixel1.text()) > 0):
                x1.append(float(self.pixel1.text()))
            if (float(self.pixel2.text()) > 0):
                x1.append(float(self.pixel2.text()))
            if (float(self.pixel3.text()) > 0):
                x1.append(float(self.pixel3.text()))
            if (float(self.pixel4.text()) > 0):
                x1.append(float(self.pixel4.text()))
            if (float(self.pixel5.text()) > 0):
                x1.append(float(self.pixel5.text()))
            if (float(self.pixel6.text()) > 0):
                x1.append(float(self.pixel6.text()))
            if (float(self.pixel7.text()) > 0):
                x1.append(float(self.pixel7.text()))
            if (float(self.pixel8.text()) > 0):
                x1.append(float(self.pixel8.text()))
            if (float(self.pixel9.text()) > 0):
                x1.append(float(self.pixel9.text()))
            if (float(self.pixel10.text()) > 0):
                x1.append(float(self.pixel10.text()))
                
            if (float(self.lambda1.text()) > 0):
                y1.append(float(self.lambda1.text()))
            if (float(self.lambda2.text()) > 0):
                y1.append(float(self.lambda2.text()))
            if (float(self.lambda3.text()) > 0):
                y1.append(float(self.lambda3.text()))
            if (float(self.lambda4.text()) > 0):
                y1.append(float(self.lambda4.text()))
            if (float(self.lambda5.text()) > 0):
                y1.append(float(self.lambda5.text()))
            if (float(self.lambda6.text()) > 0):
                y1.append(float(self.lambda6.text()))
            if (float(self.lambda7.text()) > 0):
                y1.append(float(self.lambda7.text()))
            if (float(self.lambda8.text()) > 0):
                y1.append(float(self.lambda8.text()))
            if (float(self.lambda9.text()) > 0):
                y1.append(float(self.lambda9.text()))
            if (float(self.lambda10.text()) > 0):
                y1.append(float(self.lambda10.text()))
            
            if len(x1) != len(y1):
                raise Exception ("The quantity of lambda and pixel have to be the same")
            z1 = np.polyfit(x1, y1, 3)
            p0 = []
            for i in range(len(z1)):
                e = str(z1[i]).find('e')
                
                if e > 0:
                    p0.extend([float(str(z1[i])[:e:]),int(str(z1[i])[e+1::])])
                else:
                    p0.append(float(str(z1[i])[:e:]))
                    
            _translate = QtCore.QCoreApplication.translate
            check_numb = 0
            if isinstance(p0[check_numb + 1],int):
                self.a3_label.setText(_translate("w_calibration", (str(np.around(p0[check_numb],3)))+'e'+str(p0[check_numb+1])))
                ui.a3.setText(str(np.around(p0[check_numb],3)))
                ui.e3.setText(str(p0[check_numb+1]))
                check_numb += 2
            else:
                self.a3_label.setText(_translate("w_calibration", (str(np.around(p0[check_numb],3)))))
                ui.a3.setText(str(np.around(p0[check_numb],3)))
                check_numb += 1
                
            if isinstance(p0[check_numb + 1],int):
                self.a2_label.setText(_translate("w_calibration", (str(np.around(p0[check_numb],3)))+'e'+str(p0[check_numb+1])))
                ui.a2.setText(str(np.around(p0[check_numb],3)))
                ui.e2.setText(str(p0[check_numb+1]))
                check_numb += 2
            else:
                self.a2_label.setText(_translate("w_calibration", (str(np.around(p0[check_numb],3)))))
                ui.a2.setText(str(np.around(p0[check_numb],3)))
                check_numb += 1
                
            if isinstance(p0[check_numb + 1],int):
                self.a1_label.setText(_translate("w_calibration", (str(np.around(p0[check_numb],3)))+'e'+str(p0[check_numb+1])))
                ui.a1.setText(str(np.around(p0[check_numb],3)))
                ui.e1.setText(p0[check_numb+1])
                check_numb += 2
            else:
                self.a1_label.setText(_translate("w_calibration", (str(np.around(p0[check_numb],3)))))
                ui.a1.setText(str(np.around(p0[check_numb],3)))
                check_numb += 1
                
            if len(p0) != check_numb+1:
                self.a0_label.setText(_translate("w_calibration", str(np.around(p0[check_numb],3))+'e'+str(p0[check_numb+1])))
                ui.a0.setText(str(np.around(p0[check_numb],3)))
                ui.e0.setText(p0[check_numb+1])
            else:
                self.a0_label.setText(_translate("w_calibration", str(np.around(p0[check_numb],3))))
                ui.a0.setText(str(np.around(p0[check_numb],3)))
          
            check = wavelength_convert()
            if check != 1:
                raise Exception
            check = ui.draw_wavelength_graph_signal()
            if check != 1:
                raise Exception
            check = self.w_draw_wgraph()
            if check != 1:
                raise Exception
            c_draw_wgraph = 1
            ui.statusbar.showMessage("Wavelength Equation Calculate Complete")
            return 1
        except Exception as e:
            print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e))
            ui.statusbar.showMessage("Wavelength Calculate ERROR")
            return 0
      
    def w_draw_wgraph(self):
        try:
            self.c_wavelength_graph.clear()
            x = wdata
            if ui.sg_filter_checkbox.isChecked():
                #savgol_filter(data, window length, polyorder)
                y = signal.savgol_filter(ncolmean, int(ui.window_length_edit.text()), int(ui.polyorder_edit.text()))
            else:
                y = ncolmean
            self.c_wavelength_graph.plot(x, y, pen=pg.mkPen('k'))   
            return 1
        except Exception as e:
            print('error:{}'.format(e))
            return 0
    
    def ar_autopeak_checkbox_check(self):
        if self.ar_autopeak_checkbox.isChecked() == True:
            _translate = QtCore.QCoreApplication.translate
            self.model_comboBox.setItemText(0, _translate("w_calibration", "Ocean Optics HG-1"))
            self.ar_autofindpeak_btn.setEnabled(True)
            self.lambda1.setEnabled(False)
            self.lambda2.setEnabled(False)
            self.lambda3.setEnabled(False)
            self.lambda4.setEnabled(False)
            self.lambda5.setEnabled(False)
            self.lambda6.setEnabled(False)
            self.lambda7.setEnabled(False)
            self.lambda8.setEnabled(False)
            self.lambda9.setEnabled(False)
            self.lambda10.setEnabled(False)
            
            hgar_temp[0] = self.lambda1.text()
            hgar_temp[1] = self.lambda2.text()
            hgar_temp[2] = self.lambda3.text()
            hgar_temp[3] = self.lambda4.text()
            hgar_temp[4] = self.lambda5.text()
            hgar_temp[5] = self.lambda6.text()
            hgar_temp[6] = self.lambda7.text()
            hgar_temp[7] = self.lambda8.text()
            hgar_temp[8] = self.lambda9.text()
            hgar_temp[9] = self.lambda10.text()
            
            self.lambda1.setText(config['calibration_peak']['lamdba1'])
            self.lambda2.setText(config['calibration_peak']['lamdba2'])
            self.lambda3.setText(config['calibration_peak']['lamdba3'])
            self.lambda4.setText(config['calibration_peak']['lamdba4'])
            self.lambda5.setText(config['calibration_peak']['lamdba5'])
            self.lambda6.setText(config['calibration_peak']['lamdba6'])
            self.lambda7.setText(config['calibration_peak']['lamdba7'])
            self.lambda8.setText(config['calibration_peak']['lamdba8'])
            self.lambda9.setText(config['calibration_peak']['lamdba9'])
            self.lambda10.setText(config['calibration_peak']['lamdba10'])
        else:
            _translate = QtCore.QCoreApplication.translate
            self.model_comboBox.setItemText(0, _translate("w_calibration", " "))
            self.ar_autofindpeak_btn.setEnabled(False)
            self.lambda1.setEnabled(True)
            self.lambda2.setEnabled(True)
            self.lambda3.setEnabled(True)
            self.lambda4.setEnabled(True)
            self.lambda5.setEnabled(True)
            self.lambda6.setEnabled(True)
            self.lambda7.setEnabled(True)
            self.lambda8.setEnabled(True)
            self.lambda9.setEnabled(True)
            self.lambda10.setEnabled(True)
            
            self.lambda1.setText(hgar_temp[0])
            self.lambda2.setText(hgar_temp[1])
            self.lambda3.setText(hgar_temp[2])
            self.lambda4.setText(hgar_temp[3])
            self.lambda5.setText(hgar_temp[4])
            self.lambda6.setText(hgar_temp[5])
            self.lambda7.setText(hgar_temp[6])
            self.lambda8.setText(hgar_temp[7])
            self.lambda9.setText(hgar_temp[8])
            self.lambda10.setText(hgar_temp[9])
    # 執行 thread_3
    def ar_autofindpeak_btn_clicked(self):
        thread3 = threading.Thread(target = thread_3)
        thread3.daemon = True
        thread3.start()
    
    def update_pixel(self):
        self.pixel1.setText(str(hg_peaks[0]))
        self.pixel2.setText(str(hg_peaks[1]))
        self.pixel3.setText(str(hg_peaks[2]))
        self.pixel4.setText(str(ar_peaks[0]))
        self.pixel5.setText(str(ar_peaks[1]))
        self.pixel6.setText(str(ar_peaks[2]))
        self.pixel7.setText(str(ar_peaks[3]))
        self.pixel8.setText('0')
        self.pixel9.setText('0')
        self.pixel10.setText('0')
    # Transmission window UI 設定及初始化
class UI_Transmission_Window(object):
    def setupUi(self, Transmission_window):
        Transmission_window.setObjectName("Transmission_Window")
        Transmission_window.resize(1500, 1000)
        self.centralwidget = QtWidgets.QWidget(Transmission_window)
        self.centralwidget.setObjectName("centralwidget")
        self.shutter_label = QtWidgets.QLabel(self.centralwidget)
        self.shutter_label.setGeometry(QtCore.QRect(80, 180, 131, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.shutter_label.setFont(font)
        self.shutter_label.setObjectName("shutter_label")
        self.analogGain_label = QtWidgets.QLabel(self.centralwidget)
        self.analogGain_label.setGeometry(QtCore.QRect(80, 220, 131, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.analogGain_label.setFont(font)
        self.analogGain_label.setObjectName("analogGain_label")
        self.digitalGain_label = QtWidgets.QLabel(self.centralwidget)
        self.digitalGain_label.setGeometry(QtCore.QRect(80, 260, 131, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.digitalGain_label.setFont(font)
        self.digitalGain_label.setObjectName("digitalGain_label")
        self.listWidget = QtWidgets.QListWidget(self.centralwidget)
        self.listWidget.setGeometry(QtCore.QRect(60, 170, 381, 151))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.listWidget.setFont(font)
        self.listWidget.setObjectName("listWidget")
        self.listWidget_10 = QtWidgets.QListWidget(self.centralwidget)
        self.listWidget_10.setGeometry(QtCore.QRect(60, 414, 381, 90))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.listWidget_10.setFont(font)
        self.listWidget_10.setObjectName("listWidget")
        self.shutter_lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.shutter_lineEdit.setGeometry(QtCore.QRect(180, 190, 121, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.shutter_lineEdit.setFont(font)
        self.shutter_lineEdit.setObjectName("shutter_lineEdit")
        
        self.t1_lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.t1_lineEdit.setGeometry(QtCore.QRect(115, 430, 100, 22))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.t1_lineEdit.setFont(font)
        self.t1_lineEdit.setObjectName("t1_lineEdit")
        self.t1_1label = QtWidgets.QLabel(self.centralwidget)
        self.t1_1label.setGeometry(QtCore.QRect(250, 415, 150, 55))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.t1_1label.setFont(font)
        self.t1_1label.setObjectName("t1_1label")
        self.t2_lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.t2_lineEdit.setGeometry(QtCore.QRect(115, 465, 100, 22))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.t2_lineEdit.setFont(font)
        self.t2_lineEdit.setObjectName("t2_lineEdit")
        self.t2_1label = QtWidgets.QLabel(self.centralwidget)
        self.t2_1label.setGeometry(QtCore.QRect(250, 450, 150, 55))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.t2_1label.setFont(font)
        self.t2_1label.setObjectName("t2_1label")
        self.AnalogGain_lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.AnalogGain_lineEdit.setGeometry(QtCore.QRect(180, 230, 121, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.AnalogGain_lineEdit.setFont(font)
        self.AnalogGain_lineEdit.setObjectName("AnalogGain_lineEdit")
        self.DigitalGain_lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.DigitalGain_lineEdit.setGeometry(QtCore.QRect(180, 270, 121, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.DigitalGain_lineEdit.setFont(font)
        self.DigitalGain_lineEdit.setObjectName("DigitalGain_lineEdit")
        self.shutter_annotation_label = QtWidgets.QLabel(self.centralwidget)
        self.shutter_annotation_label.setGeometry(QtCore.QRect(320, 200, 111, 16))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.shutter_annotation_label.setFont(font)
        self.shutter_annotation_label.setObjectName("shutter_annotation_label")
        self.analogGain_annotation_label = QtWidgets.QLabel(self.centralwidget)
        self.analogGain_annotation_label.setGeometry(QtCore.QRect(320, 240, 111, 16))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.analogGain_annotation_label.setFont(font)
        self.analogGain_annotation_label.setObjectName("analogGain_annotation_label")
        self.digitalGain_annotation_label = QtWidgets.QLabel(self.centralwidget)
        self.digitalGain_annotation_label.setGeometry(QtCore.QRect(320, 280, 111, 21))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.digitalGain_annotation_label.setFont(font)
        self.digitalGain_annotation_label.setObjectName("digitalGain_annotation_label")
        self.listWidget_2 = QtWidgets.QListWidget(self.centralwidget)
        self.listWidget_2.setGeometry(QtCore.QRect(60, 40, 381, 111))
        self.listWidget_2.setObjectName("listWidget_2")
        self.machineNum_label = QtWidgets.QLabel(self.centralwidget)
        self.machineNum_label.setGeometry(QtCore.QRect(75, 50, 131, 51))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.machineNum_label.setFont(font)
        self.machineNum_label.setObjectName("machineNum_label")
        self.com_label = QtWidgets.QLabel(self.centralwidget)
        self.com_label.setGeometry(QtCore.QRect(245, 50, 131, 51))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.com_label.setFont(font)
        self.com_label.setObjectName("com_label")
        self.portbox = QtWidgets.QComboBox(self.centralwidget)
        self.portbox.setGeometry(QtCore.QRect(300, 60, 70, 28))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.portbox.setFont(font)
        self.portbox.setObjectName("portbox")
        self.refresh_btn = QtWidgets.QPushButton(self.centralwidget)
        self.refresh_btn.setGeometry(QtCore.QRect(390, 60, 33, 33))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.refresh_btn.setFont(font)
        self.refresh_btn.setObjectName("refresh_btn")
        self.MachineNum_lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.MachineNum_lineEdit.setGeometry(QtCore.QRect(183, 60, 55, 31))
        self.MachineNum_lineEdit.setObjectName("MachineNum_lineEdit")
        self.light_label = QtWidgets.QLabel(self.centralwidget)
        self.light_label.setGeometry(QtCore.QRect(80, 100, 110, 51))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.light_label.setFont(font)
        self.light_label.setObjectName("light_label")
        self.LightA_check = QtWidgets.QRadioButton(self.centralwidget)
        self.LightA_check.setGeometry(QtCore.QRect(180, 120, 98, 19))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.LightA_check.setFont(font)
        self.LightA_check.setObjectName("LightA_check")
        self.LightB_check = QtWidgets.QRadioButton(self.centralwidget)
        self.LightB_check.setGeometry(QtCore.QRect(240, 120, 98, 19))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.LightB_check.setFont(font)
        self.LightB_check.setObjectName("LightB_check")
        self.LightC_check = QtWidgets.QRadioButton(self.centralwidget)
        self.LightC_check.setGeometry(QtCore.QRect(300, 120, 98, 19))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.LightC_check.setFont(font)
        self.LightC_check.setObjectName("LightC_check")
        self.listWidget_3 = QtWidgets.QListWidget(self.centralwidget)
        self.listWidget_3.setGeometry(QtCore.QRect(60, 340, 381, 61))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.listWidget_3.setFont(font)
        self.listWidget_3.setObjectName("listWidget_3")
        self.AutoScaling_label = QtWidgets.QLabel(self.centralwidget)
        self.AutoScaling_label.setGeometry(QtCore.QRect(80, 350, 131, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.AutoScaling_label.setFont(font)
        self.AutoScaling_label.setObjectName("AutoScaling_label")
        self.t1_label = QtWidgets.QLabel(self.centralwidget)
        self.t1_label.setGeometry(QtCore.QRect(80, 415, 25, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.t1_label.setFont(font)
        self.t1_label.setObjectName("t1_label")
        self.t2_label = QtWidgets.QLabel(self.centralwidget)
        self.t2_label.setGeometry(QtCore.QRect(80, 450, 25, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.t2_label.setFont(font)
        self.t2_label.setObjectName("t1_label")
        self.listWidget_4 = QtWidgets.QListWidget(self.centralwidget)
        self.listWidget_4.setGeometry(QtCore.QRect(60, 520, 381, 355))     # 參考取樣區域
        font = QtGui.QFont()
        font.setPointSize(10)
        self.listWidget_4.setFont(font)
        self.listWidget_4.setObjectName("listWidget_4")
        self.Ref_check = QtWidgets.QRadioButton(self.centralwidget)
        self.Ref_check.setGeometry(QtCore.QRect(100, 540, 98, 19))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.Ref_check.setFont(font)
        self.Ref_check.setObjectName("Ref_check")
        self.Sample_check = QtWidgets.QRadioButton(self.centralwidget)
        self.Sample_check.setGeometry(QtCore.QRect(280, 540, 98, 19))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.Sample_check.setFont(font)
        self.Sample_check.setObjectName("Sample_check")
        self.nos_label = QtWidgets.QLabel(self.centralwidget)
        self.nos_label.setGeometry(QtCore.QRect(80, 560, 131, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.nos_label.setFont(font)
        self.nos_label.setObjectName("label_9")
        self.nos_lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.nos_lineEdit.setGeometry(QtCore.QRect(260, 570, 121, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.nos_lineEdit.setFont(font)
        self.nos_lineEdit.setObjectName("nos_lineEdit")
        self.baseline_label = QtWidgets.QLabel(self.centralwidget)
        self.baseline_label.setGeometry(QtCore.QRect(80, 590, 171, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.baseline_label.setFont(font)
        self.baseline_label.setObjectName("baseline_label")
        self.baseLineMin = QtWidgets.QLineEdit(self.centralwidget)
        self.baseLineMin.setGeometry(QtCore.QRect(80, 640, 121, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.baseLineMin.setFont(font)
        self.baseLineMin.setObjectName("baseLineMin")
        self.baseLineMax = QtWidgets.QLineEdit(self.centralwidget)
        self.baseLineMax.setGeometry(QtCore.QRect(260, 640, 121, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.baseLineMax.setFont(font)
        self.baseLineMax.setObjectName("baseLineMax")
        self.label_999 = QtWidgets.QLabel(self.centralwidget)
        self.label_999.setGeometry(QtCore.QRect(220, 630, 40, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_999.setFont(font)
        self.label_999.setObjectName("label_999")
        self.dark_label = QtWidgets.QLabel(self.centralwidget)
        self.dark_label.setGeometry(QtCore.QRect(80, 670, 171, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.dark_label.setFont(font)
        self.dark_label.setObjectName("dark_label")
        self.Dark_btn = QtWidgets.QPushButton(self.centralwidget)
        self.Dark_btn.setGeometry(QtCore.QRect(260, 680, 121, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.Dark_btn.setFont(font)
        self.Dark_btn.setObjectName("Dark_btn")
        self.AutoScaling_button = QtWidgets.QPushButton(self.centralwidget)
        self.AutoScaling_button.setGeometry(QtCore.QRect(260, 360, 121, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.AutoScaling_button.setFont(font)
        self.AutoScaling_button.setObjectName("AutoScaling_button")
        self.spectrum_label = QtWidgets.QLabel(self.centralwidget)
        self.spectrum_label.setGeometry(QtCore.QRect(80, 710, 171, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.spectrum_label.setFont(font)
        self.spectrum_label.setObjectName("spectrum_label")
        self.Spectro_btn = QtWidgets.QPushButton(self.centralwidget)
        self.Spectro_btn.setGeometry(QtCore.QRect(260, 720, 121, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.Spectro_btn.setFont(font)
        self.Spectro_btn.setObjectName("Spectro_btn")
        self.smd_label = QtWidgets.QLabel(self.centralwidget)
        self.smd_label.setGeometry(QtCore.QRect(80, 750, 171, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.smd_label.setFont(font)
        self.smd_label.setObjectName("smd_label")
        self.Smd_btn = QtWidgets.QPushButton(self.centralwidget)
        self.Smd_btn.setGeometry(QtCore.QRect(260, 760, 121, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.Smd_btn.setFont(font)
        self.Smd_btn.setObjectName("Smd_btn")
        self.smdmb_label = QtWidgets.QLabel(self.centralwidget)
        self.smdmb_label.setGeometry(QtCore.QRect(80, 780, 171, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.smdmb_label.setFont(font)
        self.smdmb_label.setObjectName("smdmb_label")
        self.Smdmb_btn = QtWidgets.QPushButton(self.centralwidget)
        self.Smdmb_btn.setGeometry(QtCore.QRect(260, 800, 121, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.Smdmb_btn.setFont(font)
        self.Smdmb_btn.setObjectName("Smdmb_btn")
        self.continuous_check = QtWidgets.QCheckBox(self.centralwidget)
        self.continuous_check.setGeometry(QtCore.QRect(80, 853, 111, 19))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.continuous_check.setFont(font)
        self.continuous_check.setObjectName("t_continuous_check")
        self.t_continuous_check = QtWidgets.QCheckBox(self.centralwidget)
        self.t_continuous_check.setGeometry(QtCore.QRect(80, 930, 111, 19))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.t_continuous_check.setFont(font)
        self.t_continuous_check.setObjectName("t_continuous_check")
        self.ref_default_check = QtWidgets.QCheckBox(self.centralwidget)
        self.ref_default_check.setGeometry(QtCore.QRect(80, 830, 130, 19))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.ref_default_check.setFont(font)
        self.ref_default_check.setObjectName("ref_default_check")
        self.trans_label = QtWidgets.QLabel(self.centralwidget)
        self.trans_label.setGeometry(QtCore.QRect(80, 890, 131, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.trans_label.setFont(font)
        self.trans_label.setObjectName("trans_label")
        self.listWidget_5 = QtWidgets.QListWidget(self.centralwidget)        # 穿透區域
        self.listWidget_5.setGeometry(QtCore.QRect(60, 890, 381, 67))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.listWidget_5.setFont(font)
        self.listWidget_5.setObjectName("listWidget_5")
        self.Trans_btn = QtWidgets.QPushButton(self.centralwidget)
        self.Trans_btn.setGeometry(QtCore.QRect(260, 900, 121, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.Trans_btn.setFont(font)
        self.Trans_btn.setObjectName("Trans_btn")
        self.listWidget_6 = QtWidgets.QListWidget(self.centralwidget)
        self.listWidget_6.setGeometry(QtCore.QRect(500, 40, 321, 111))    # SG 區域
        font = QtGui.QFont()
        font.setPointSize(10)
        self.listWidget_6.setFont(font)
        self.listWidget_6.setObjectName("listWidget_6")
        self.Sg_check = QtWidgets.QCheckBox(self.centralwidget)
        self.Sg_check.setGeometry(QtCore.QRect(520, 50, 111, 19))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.Sg_check.setFont(font)
        self.Sg_check.setObjectName("Sg_check")
        self.sg_data_label = QtWidgets.QLabel(self.centralwidget)
        self.sg_data_label.setGeometry(QtCore.QRect(520, 75, 131, 21))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.sg_data_label.setFont(font)
        self.sg_data_label.setObjectName("label_18")
        self.SgPoint_lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.SgPoint_lineEdit.setGeometry(QtCore.QRect(670, 60, 101, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.SgPoint_lineEdit.setFont(font)
        self.SgPoint_lineEdit.setObjectName("SgPoint_lineEdit")
        self.SgOrder_lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.SgOrder_lineEdit.setGeometry(QtCore.QRect(670, 100, 101, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.SgOrder_lineEdit.setFont(font)
        self.SgOrder_lineEdit.setObjectName("SgOrder_lineEdit")
        self.sg_order_label = QtWidgets.QLabel(self.centralwidget)
        self.sg_order_label.setGeometry(QtCore.QRect(520, 90, 131, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.sg_order_label.setFont(font)
        self.sg_order_label.setObjectName("sg_order_label")
        self.listWidget_7 = QtWidgets.QListWidget(self.centralwidget)
        self.listWidget_7.setGeometry(QtCore.QRect(1080, 20, 331, 311))     # 存檔區域
        font = QtGui.QFont()
        font.setPointSize(10)
        self.listWidget_7.setFont(font)
        self.listWidget_7.setObjectName("listWidget_7")
        self.savefunction_label = QtWidgets.QLabel(self.centralwidget)
        self.savefunction_label.setGeometry(QtCore.QRect(1100, 20, 131, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.savefunction_label.setFont(font)
        self.savefunction_label.setObjectName("savefunction_label")
        self.databox = QtWidgets.QComboBox(self.centralwidget)
        self.databox.setGeometry(QtCore.QRect(1270, 30, 121, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.databox.setFont(font)
        self.databox.setObjectName("databox")
        self.databox.addItem("")
        self.databox.addItem("")
        self.databox.addItem("")
        self.databox.addItem("")
        self.databox.addItem("")
        self.databox.addItem("")
        self.databox.addItem("")
        self.SaveRaw_check = QtWidgets.QCheckBox(self.centralwidget)
        self.SaveRaw_check.setGeometry(QtCore.QRect(1100, 70, 111, 19))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.SaveRaw_check.setFont(font)
        self.SaveRaw_check.setObjectName("SaveRaw_check")
        self.SaveSg_check = QtWidgets.QCheckBox(self.centralwidget)
        self.SaveSg_check.setGeometry(QtCore.QRect(1100, 100, 111, 19))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.SaveSg_check.setFont(font)
        self.SaveSg_check.setObjectName("SaveSg_check")
        self.savefilename_label = QtWidgets.QLabel(self.centralwidget)
        self.savefilename_label.setGeometry(QtCore.QRect(1100, 110, 131, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.savefilename_label.setFont(font)
        self.savefilename_label.setObjectName("savefilename_label")
        self.SaveFName_lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.SaveFName_lineEdit.setGeometry(QtCore.QRect(1100, 150, 261, 41))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.SaveFName_lineEdit.setFont(font)
        self.SaveFName_lineEdit.setObjectName("SaveFName_lineEdit")
        self.browsepath_label = QtWidgets.QLabel(self.centralwidget)
        self.browsepath_label.setGeometry(QtCore.QRect(1100, 180, 131, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.browsepath_label.setFont(font)
        self.browsepath_label.setObjectName("browsepath_label")
        self.BrowsePath_lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.BrowsePath_lineEdit.setGeometry(QtCore.QRect(1100, 230, 261, 41))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.BrowsePath_lineEdit.setFont(font)
        self.BrowsePath_lineEdit.setObjectName("BrowsePath_lineEdit")
        self.Browse_btn = QtWidgets.QPushButton(self.centralwidget)
        self.Browse_btn.setGeometry(QtCore.QRect(1100, 280, 121, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.Browse_btn.setFont(font)
        self.Browse_btn.setObjectName("Browse_btn")
        self.saveData_btn = QtWidgets.QPushButton(self.centralwidget)
        self.saveData_btn.setGeometry(QtCore.QRect(1260, 280, 121, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.saveData_btn.setFont(font)
        self.saveData_btn.setObjectName("saveData_btn")
        self.listWidget_8 = QtWidgets.QListWidget(self.centralwidget)
        self.listWidget_8.setGeometry(QtCore.QRect(1080, 350, 181, 241))      # axis 1 區域
        self.listWidget_8.setObjectName("listWidget_8")
        self.label_25 = QtWidgets.QLabel(self.centralwidget)
        self.label_25.setGeometry(QtCore.QRect(1140, 350, 131, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_25.setFont(font)
        self.label_25.setObjectName("label_25")
        self.Graph1_Ymin = QtWidgets.QLineEdit(self.centralwidget)
        self.Graph1_Ymin.setGeometry(QtCore.QRect(1090, 400, 61, 31))
        self.Graph1_Ymin.setObjectName("Graph1_Ymin")
        self.Graph1_Ymax = QtWidgets.QLineEdit(self.centralwidget)
        self.Graph1_Ymax.setGeometry(QtCore.QRect(1180, 400, 61, 31))
        self.Graph1_Ymax.setObjectName("Graph1_Ymax")
        self.Graph1_Yauto = QtWidgets.QRadioButton(self.centralwidget)
        self.Graph1_Yauto.setGeometry(QtCore.QRect(1100, 440, 98, 19))
        self.Graph1_Yauto.setObjectName("Graph1_Yauto")
        self.Graph1_yYfix = QtWidgets.QRadioButton(self.centralwidget)
        self.Graph1_yYfix.setGeometry(QtCore.QRect(1180, 440, 98, 19))
        self.Graph1_yYfix.setObjectName("Graph1_yYfix")
        self.label_26 = QtWidgets.QLabel(self.centralwidget)
        self.label_26.setGeometry(QtCore.QRect(1140, 450, 131, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_26.setFont(font)
        self.label_26.setObjectName("label_26")
        self.Graph1_Xmin = QtWidgets.QLineEdit(self.centralwidget)
        self.Graph1_Xmin.setGeometry(QtCore.QRect(1090, 500, 61, 31))
        self.Graph1_Xmin.setObjectName("Graph1_Xmin")
        self.Graph1_Xmax = QtWidgets.QLineEdit(self.centralwidget)
        self.Graph1_Xmax.setGeometry(QtCore.QRect(1180, 500, 61, 31))
        self.Graph1_Xmax.setObjectName("Graph1_Xmax")
        self.Graph1_Xauto = QtWidgets.QRadioButton(self.centralwidget)
        self.Graph1_Xauto.setGeometry(QtCore.QRect(1100, 550, 98, 19))
        self.Graph1_Xauto.setObjectName("Graph1_Xauto")
        self.Graph1_Xfix = QtWidgets.QRadioButton(self.centralwidget)
        self.Graph1_Xfix.setGeometry(QtCore.QRect(1180, 550, 98, 19))
        self.Graph1_Xfix.setObjectName("Graph1_Xfix")
        self.Graph2_Xfix = QtWidgets.QRadioButton(self.centralwidget)
        self.Graph2_Xfix.setGeometry(QtCore.QRect(1180, 920, 98, 19))
        self.Graph2_Xfix.setObjectName("Graph2_Xfix")
        self.Graph2_Yauto = QtWidgets.QRadioButton(self.centralwidget)
        self.Graph2_Yauto.setGeometry(QtCore.QRect(1100, 810, 98, 19))
        self.Graph2_Yauto.setObjectName("Graph2_Yauto")
        self.label_27 = QtWidgets.QLabel(self.centralwidget)
        self.label_27.setGeometry(QtCore.QRect(1140, 820, 131, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_27.setFont(font)
        self.label_27.setObjectName("label_27")
        self.listWidget_9 = QtWidgets.QListWidget(self.centralwidget)
        self.listWidget_9.setGeometry(QtCore.QRect(1080, 720, 181, 241))     
        self.listWidget_9.setObjectName("listWidget_9")
        self.Graph2_Xmin = QtWidgets.QLineEdit(self.centralwidget)
        self.Graph2_Xmin.setGeometry(QtCore.QRect(1090, 870, 61, 31))
        self.Graph2_Xmin.setObjectName("Graph2_Xmin")
        self.Graph2_Xmax = QtWidgets.QLineEdit(self.centralwidget)
        self.Graph2_Xmax.setGeometry(QtCore.QRect(1180, 870, 61, 31))
        self.Graph2_Xmax.setObjectName("Graph2_Xmax")
        self.label_28 = QtWidgets.QLabel(self.centralwidget)
        self.label_28.setGeometry(QtCore.QRect(1140, 720, 131, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_28.setFont(font)
        self.label_28.setObjectName("label_28")
        self.Graph2_Ymin = QtWidgets.QLineEdit(self.centralwidget)
        self.Graph2_Ymin.setGeometry(QtCore.QRect(1090, 770, 61, 31))
        self.Graph2_Ymin.setObjectName("Graph2_Ymin")
        self.Graph2_Xauto = QtWidgets.QRadioButton(self.centralwidget)
        self.Graph2_Xauto.setGeometry(QtCore.QRect(1100, 920, 98, 19))
        self.Graph2_Xauto.setObjectName("Graph2_Xauto")
        self.Graph2_Yfix = QtWidgets.QRadioButton(self.centralwidget)
        self.Graph2_Yfix.setGeometry(QtCore.QRect(1180, 810, 98, 19))
        self.Graph2_Yfix.setObjectName("Graph2_Yfix")
        self.Graph2_Ymax = QtWidgets.QLineEdit(self.centralwidget)
        self.Graph2_Ymax.setGeometry(QtCore.QRect(1180, 770, 61, 31))
        self.Graph2_Ymax.setObjectName("Graph2_Ymax")
        self.spectro_graph = pg.PlotWidget(self.centralwidget)
        self.spectro_graph.setGeometry(QtCore.QRect(490, 170, 551, 391))
        self.transmission_graph = pg.PlotWidget(self.centralwidget)
        self.transmission_graph.setGeometry(QtCore.QRect(490, 580, 551, 391))
        self.spectro_graph.setBackground('w')
        self.spectro_graph.setLabel('left', 'Intensity')
        self.spectro_graph.setLabel('bottom', 'Lambda')
        self.transmission_graph.setBackground('w')
        self.transmission_graph.setLabel('left', 'Intensity')
        self.transmission_graph.setLabel('bottom', 'Lambda')
        self.listWidget_9.raise_()
        self.listWidget_7.raise_()
        self.listWidget_6.raise_()
        self.listWidget_5.raise_()
        self.listWidget.raise_()
        self.shutter_label.raise_()
        self.analogGain_label.raise_()
        self.t1_label.raise_()
        self.t1_lineEdit.raise_()
        self.t2_label.raise_()
        self.t2_lineEdit.raise_()
        self.digitalGain_label.raise_()
        self.shutter_lineEdit.raise_()
        self.AnalogGain_lineEdit.raise_()
        self.DigitalGain_lineEdit.raise_()
        self.shutter_annotation_label.raise_()
        self.analogGain_annotation_label.raise_()
        self.digitalGain_annotation_label.raise_()
        self.listWidget_2.raise_()
        self.machineNum_label.raise_()
        self.MachineNum_lineEdit.raise_()
        self.light_label.raise_()
        self.LightA_check.raise_()
        self.LightB_check.raise_()
        self.t2_1label.raise_()
        self.LightC_check.raise_()
        self.listWidget_3.raise_()
        self.AutoScaling_label.raise_()
        self.com_label.raise_()
        self.listWidget_4.raise_()
        self.Ref_check.raise_()
        self.Sample_check.raise_()
        self.t1_1label.raise_()
        self.nos_label.raise_()
        self.nos_lineEdit.raise_()
        self.baseline_label.raise_()
        self.baseLineMin.raise_()
        self.baseLineMax.raise_()
        self.label_999.raise_()
        self.ref_default_check.raise_()
        self.dark_label.raise_()
        self.refresh_btn.raise_()
        self.Dark_btn.raise_()
        self.AutoScaling_button.raise_()
        self.spectrum_label.raise_()
        self.Spectro_btn.raise_()
        self.smd_label.raise_()
        self.Smd_btn.raise_()
        self.smdmb_label.raise_()
        self.Smdmb_btn.raise_()
        self.continuous_check.raise_()
        self.t_continuous_check.raise_()
        self.trans_label.raise_()
        self.Trans_btn.raise_()
        self.Sg_check.raise_()
        self.sg_data_label.raise_()
        self.SgPoint_lineEdit.raise_()
        self.SgOrder_lineEdit.raise_()
        self.sg_order_label.raise_()
        self.savefunction_label.raise_()
        self.databox.raise_()
        self.portbox.raise_()
        self.SaveRaw_check.raise_()
        self.SaveSg_check.raise_()
        self.savefilename_label.raise_()
        self.SaveFName_lineEdit.raise_()
        self.browsepath_label.raise_()
        self.BrowsePath_lineEdit.raise_()
        self.Browse_btn.raise_()
        self.saveData_btn.raise_()
        self.listWidget_8.raise_()
        self.label_25.raise_()
        self.Graph1_Ymin.raise_()
        self.Graph1_Ymax.raise_()
        self.Graph1_Yauto.raise_()
        self.Graph1_yYfix.raise_()
        self.label_26.raise_()
        self.Graph1_Xmin.raise_()
        self.Graph1_Xmax.raise_()
        self.Graph1_Xauto.raise_()
        self.Graph1_Xfix.raise_()
        self.Graph2_Xfix.raise_()
        self.Graph2_Yauto.raise_()
        self.label_27.raise_()
        self.Graph2_Xmin.raise_()
        self.Graph2_Xmax.raise_()
        self.label_28.raise_()
        self.Graph2_Ymin.raise_()
        self.Graph2_Xauto.raise_()
        self.Graph2_Yfix.raise_()
        self.Graph2_Ymax.raise_()
        self.Graph2_Xfix.raise_()
        Transmission_window.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(Transmission_window)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1724, 21))
        self.menubar.setObjectName("menubar")
        Transmission_window.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(Transmission_window)
        self.statusbar.setObjectName("statusbar")
        Transmission_window.setStatusBar(self.statusbar)

        self.retranslateUi(Transmission_window)
        QtCore.QMetaObject.connectSlotsByName(Transmission_window)

    def retranslateUi(self, Transmission_window):
        _translate = QtCore.QCoreApplication.translate
        Transmission_window.setWindowTitle(_translate("Transmission_Window", "Transmission_Window"))
        self.shutter_label.setText(_translate("Transmission_Window", "Shutter"))
        self.analogGain_label.setText(_translate("Transmission_Window", "Analog Gain"))
        self.digitalGain_label.setText(_translate("Transmission_Window", "Digital Gain"))
        self.shutter_annotation_label.setText(_translate("Transmission_Window", "Max:1000000μs"))
        self.analogGain_annotation_label.setText(_translate("Transmission_Window", "Max:100000000"))
        self.digitalGain_annotation_label.setText(_translate("Transmission_Window", "Not Functioning"))
        self.machineNum_label.setText(_translate("Transmission_Window", "Machine num :"))
        self.light_label.setText(_translate("Transmission_Window", "Light"))
        self.com_label.setText(_translate("Transmission_Window", "COM : "))
        self.t1_label.setText(_translate("Transmission_Window", "T1 :"))
        self.t2_label.setText(_translate("Transmission_Window", "T2 :"))
        self.LightA_check.setText(_translate("Transmission_Window", "A"))
        self.LightB_check.setText(_translate("Transmission_Window", "B"))
        self.LightC_check.setText(_translate("Transmission_Window", "C"))
        self.AutoScaling_label.setText(_translate("Transmission_Window", "Auto Scaling"))
        self.Ref_check.setText(_translate("Transmission_Window", "Reference"))
        self.Sample_check.setText(_translate("Transmission_Window", "Sample"))
        self.nos_label.setText(_translate("Transmission_Window", "Num of scan"))
        self.baseline_label.setText(_translate("Transmission_Window", "BaseLine range"))
        self.label_999.setText(_translate("Transmission_Window", "～"))
        self.dark_label.setText(_translate("Transmission_Window", "Dark"))
        self.Dark_btn.setText(_translate("Transmission_Window", "Start"))
        self.AutoScaling_button.setText(_translate("Transmission_Window", "Start"))
        self.spectrum_label.setText(_translate("Transmission_Window", "Spectrum"))
        self.Spectro_btn.setText(_translate("Transmission_Window", "Start"))
        self.smd_label.setText(_translate("Transmission_Window", "S - D"))
        self.Smd_btn.setText(_translate("Transmission_Window", "Start"))
        self.smdmb_label.setText(_translate("Transmission_Window", "S - D - B"))
        self.Smdmb_btn.setText(_translate("Transmission_Window", "Start"))
        self.continuous_check.setText(_translate("Transmission_Window", "Continuous"))
        self.t_continuous_check.setText(_translate("Transmission_Window", "Continuous"))
        self.trans_label.setText(_translate("Transmission_Window", "Transmission"))
        self.Trans_btn.setText(_translate("Transmission_Window", "Start"))
        self.Sg_check.setText(_translate("Transmission_Window", "SG Filter"))
        self.sg_data_label.setText(_translate("Transmission_Window", "Data Point"))
        self.sg_order_label.setText(_translate("Transmission_Window", "Poly Order"))
        self.savefunction_label.setText(_translate("Transmission_Window", "Save Function"))
        self.databox.setItemText(0,_translate("Transmission_Window", "Ref Default"))
        self.databox.setItemText(1, _translate("Transmission_Window", "Dark"))
        self.databox.setItemText(2, _translate("Transmission_Window", "Spectrum"))
        self.databox.setItemText(3, _translate("Transmission_Window", "S - D"))
        self.databox.setItemText(4, _translate("Transmission_Window", "S - D - B"))
        self.databox.setItemText(5, _translate("Transmission_Window", "Transmission"))
        self.databox.setItemText(6, _translate("Transmission_Window", "All"))
        self.SaveRaw_check.setText(_translate("Transmission_Window", "Raw Data"))
        self.SaveSg_check.setText(_translate("Transmission_Window", "SG Data"))
        self.ref_default_check.setText(_translate("Transmission_Window", "Ref default data"))
        self.savefilename_label.setText(_translate("Transmission_Window", "Save File Name"))
        self.browsepath_label.setText(_translate("Transmission_Window", "Browse Path"))
        self.Browse_btn.setText(_translate("Transmission_Window", "Browse"))
        self.saveData_btn.setText(_translate("Transmission_Window", "Save"))
        self.label_25.setText(_translate("Transmission_Window", "Y Axis"))
        self.Graph1_Yauto.setText(_translate("Transmission_Window", "AUTO"))
        self.Graph1_yYfix.setText(_translate("Transmission_Window", "FIX"))
        self.label_26.setText(_translate("Transmission_Window", "X Axis"))
        self.Graph1_Xauto.setText(_translate("Transmission_Window", "AUTO"))
        self.Graph1_Xfix.setText(_translate("Transmission_Window", "FIX"))
        self.Graph2_Xfix.setText(_translate("Transmission_Window", "FIX"))
        self.Graph2_Yauto.setText(_translate("Transmission_Window", "AUTO"))
        self.label_27.setText(_translate("Transmission_Window", "X Axis"))
        self.label_28.setText(_translate("Transmission_Window", "Y Axis"))
        self.Graph2_Xauto.setText(_translate("Transmission_Window", "AUTO"))
        self.Graph2_Yfix.setText(_translate("Transmission_Window", "FIX"))
        self.t1_1label.setText(_translate("Transmission_Window", "Open light waiting time"))
        self.t2_1label.setText(_translate("Transmission_Window", "Close light waiting time"))

        self.refresh_btn.setIcon(QtGui.QIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload)))
        self.light_buttongroup = QtWidgets.QButtonGroup(Transmission_window)
        self.light_buttongroup.addButton(self.LightA_check)
        self.light_buttongroup.addButton(self.LightB_check)
        self.light_buttongroup.addButton(self.LightC_check)

        self.spectrum_mode_buttongroup = QtWidgets.QButtonGroup(Transmission_window)
        self.spectrum_mode_buttongroup.addButton(self.Ref_check)
        self.spectrum_mode_buttongroup.addButton(self.Sample_check)

        self.Yaxis_buttongroup = QtWidgets.QButtonGroup(Transmission_window)
        self.Yaxis_buttongroup.addButton(self.Graph1_Yauto)
        self.Yaxis_buttongroup.addButton(self.Graph1_yYfix)

        self.Xaxis_buttongroup = QtWidgets.QButtonGroup(Transmission_window)
        self.Xaxis_buttongroup.addButton(self.Graph1_Xauto)
        self.Xaxis_buttongroup.addButton(self.Graph1_Xfix)

        self.Yaxis2_buttongroup = QtWidgets.QButtonGroup(Transmission_window)
        self.Yaxis2_buttongroup.addButton(self.Graph2_Yauto)
        self.Yaxis2_buttongroup.addButton(self.Graph2_Yfix)

        self.Xaxis2_buttongroup = QtWidgets.QButtonGroup(Transmission_window)
        self.Xaxis2_buttongroup.addButton(self.Graph2_Xauto)
        self.Xaxis2_buttongroup.addButton(self.Graph2_Xfix)

        self.MachineNum_lineEdit.setEnabled(False)
        self.Dark_btn.setEnabled(False)
        self.Spectro_btn.setEnabled(False)
        self.Smd_btn.setEnabled(False)
        self.Smdmb_btn.setEnabled(False)
        self.nos_lineEdit.setEnabled(False)
        self.baseLineMin.setEnabled(False)
        self.baseLineMax.setEnabled(False)
        self.t_continuous_check.setEnabled(False)
        self.Trans_btn.setEnabled(False)
        self.Trans_btn.setEnabled(False)
        self.SgPoint_lineEdit.setEnabled(False)
        self.SgOrder_lineEdit.setEnabled(False)
        self.saveData_btn.setEnabled(True)
        self.ref_default_check.setEnabled(False)
        self.continuous_check.setEnabled(False)
        self.Browse_btn.setEnabled(False)
        self.BrowsePath_lineEdit.setEnabled(False)
        self.SaveFName_lineEdit.setEnabled(False)
        self.Graph1_Ymin.setEnabled(False)
        self.Graph1_Ymax.setEnabled(False)
        self.Graph1_Xmin.setEnabled(False)
        self.Graph1_Xmax.setEnabled(False)
        self.Graph2_Ymin.setEnabled(False)
        self.Graph2_Ymax.setEnabled(False)
        self.Graph2_Xmin.setEnabled(False)
        self.Graph2_Xmax.setEnabled(False)

        self.Graph1_Yauto.setChecked(True)
        self.Graph1_Xauto.setChecked(True)
        self.Graph2_Yauto.setChecked(True)
        self.Graph2_Xauto.setChecked(True)

        self.shutter_lineEdit.setText(str(1000))
        self.AnalogGain_lineEdit.setText(str(0))
        self.DigitalGain_lineEdit.setText(str(0))
        self.nos_lineEdit.setText(str(1))
        self.t1_lineEdit.setText(str(5))
        self.t2_lineEdit.setText(str(5))
        self.Graph1_Ymin.setText(y_axis_min)
        self.Graph1_Ymax.setText(y_axis_max)
        self.Graph1_Xmin.setText(x_axis_min)
        self.Graph1_Xmax.setText(x_axis_max)
        self.Graph2_Ymin.setText(str(0))
        self.Graph2_Ymax.setText(str(1.2))
        self.Graph2_Xmin.setText(str(600))
        self.Graph2_Xmax.setText(str(850))

        signalComm.bo_new_data.connect(self.bo_update_wdata)

        #TODO
        self.Ref_check.clicked.connect(self.ref_check)
        self.Sample_check.clicked.connect(self.sample_check)
        self.Dark_btn.clicked.connect(self.dark_spectro)
        self.Spectro_btn.clicked.connect(self.spectro)
        self.Smd_btn.clicked.connect(self.smd)
        self.Smdmb_btn.clicked.connect(self.smdmb)
        self.Trans_btn.clicked.connect(self.trans)
        self.Sg_check.clicked.connect(self.sg_check)
        self.saveData_btn.clicked.connect(self.saveData_bo)
        self.AutoScaling_button.clicked.connect(self.autoscaling)
        self.Browse_btn.clicked.connect(self.browse_path_bo)
        self.refresh_btn.clicked.connect(self.refresh_com)
        self.LightA_check.clicked.connect(self.reset_shutter)
        self.LightB_check.clicked.connect(self.reset_shutter)
        self.LightC_check.clicked.connect(self.reset_shutter)
        self.Graph1_Yauto.clicked.connect(self.y_axis_clicked_t)
        self.Graph1_yYfix.clicked.connect(self.y_axis_clicked_t)
        self.Graph1_Xauto.clicked.connect(self.x_axis_clicked_t)
        self.Graph1_Xfix.clicked.connect(self.x_axis_clicked_t)
        self.Graph2_Yauto.clicked.connect(self.y_axis2_clicked_t)
        self.Graph2_Yfix.clicked.connect(self.y_axis2_clicked_t)
        self.Graph2_Xfix.clicked.connect(self.x_axis2_clicked_t)
        self.Graph2_Xauto.clicked.connect(self.x_axis2_clicked_t)
        self.SaveRaw_check.toggled.connect(self.save_data_ckeck)
        self.SaveSg_check.toggled.connect(self.save_data_ckeck)
        self.ref_default_check.toggled.connect(self.Ref_default_check)
        self.continuous_check.toggled.connect(self.Continuous_check)
        self.t_continuous_check.toggled.connect(self.t_Continuous_check)
        self.Sg_check.toggled.connect(self.SG_check)
        self.databox.currentIndexChanged.connect(self.save_data_ckeck)
        self.portbox.currentIndexChanged.connect(self.com_connect)

        self.Graph1_Ymin.textChanged[str].connect(self.y_axis_fix_t)
        self.Graph1_Ymax.textChanged[str].connect(self.y_axis_fix_t)
        self.Graph1_Xmin.textChanged[str].connect(self.x_axis_fix_t)
        self.Graph1_Xmax.textChanged[str].connect(self.x_axis_fix_t)
        self.Graph2_Ymin.textChanged[str].connect(self.y_axis2_fix_t)
        self.Graph2_Ymax.textChanged[str].connect(self.y_axis2_fix_t)
        self.Graph2_Xmin.textChanged[str].connect(self.x_axis2_fix_t)
        self.Graph2_Xmax.textChanged[str].connect(self.x_axis2_fix_t)

    def com_connect(self):
        ser.port = self.portbox.currentText()
        s = self.portbox.currentText()
        if(s == "none"):
            print("Not found")
        else:    
            print('found' + s)
        
    def light_open(self):
        try:
            t1 = int(self.t1_lineEdit.text())
            ser.close()
            check = self.spectroPara_check()
            if(check == 1):
                ser.open()
            light_open_helper = self.light_choose() + "1#"
            ser.write(light_open_helper.encode())
            r = ser.read(4)
            time.sleep(t1)
            print("Open :{}".format(r))
            return 1
        except Exception as e:
            print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e))
        return 0

    def light_close(self):
        try:
            light_close_helper = self.light_choose() + "0#"
            ser.write(light_close_helper.encode())
            r = ser.read(4)
            ser.close()
            print(r)
            return 1
        except Exception as e:
            print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e))
        return 0
    
    def reset_shutter(self):
        try:
            self.shutter_lineEdit.setText(str(1000))
        except Exception as e:
            print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e))
        return 0
    def autoscaling(self):
        global auto_mode,window_num,t_button_check
        try:
            auto_mode = 0
            window_num = 3
            t_button_check = 0
            self.Spectro_btn.setEnabled(False)
            self.Dark_btn.setEnabled(False)
            self.Smd_btn.setEnabled(False)
            self.Smdmb_btn.setEnabled(False)
            thread2 = threading.Thread(target = thread_2)
            thread2.daemon = True
            thread2.start()
        except Exception as e:
            print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e))
            return 0  
        
    def dark_spectro(self):
        global spectro_mode,bo_mode,window_num
        try:
            spectro_mode = self.spectroMode_check()             # 判斷是Ref(1) 還是 Sample mode(2) 因矩陣要分開存
            if(self.ref_default_check.isChecked() and spectro_mode == 1):
                window_num = 10
                self.read_ref_default()
                self.sgProcess(Dark_data)
                self.smdBtn_checkable()
            elif(self.Dark_btn.text() == "Stop"):
                self.continuous_check.setChecked(False)
            else:
                bo_mode = 0
                window_num = 4
                paracheck = self.darkPara_check()                   # 判斷有無缺漏參數 沒有缺漏 return 1
                if(paracheck == 1):
                    thread4 = threading.Thread(target = thread_4,args = (window_num,))
                    thread4.start()
        except Exception as e:
            print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e))
            return 0    
        
    def spectro(self):
        global spectro_mode,bo_mode,window_num,t_button_check
        try:
            spectro_mode = self.spectroMode_check()              # 判斷是Ref(1) 還是 Sample mode(2) 因矩陣要分開存 
            if(self.ref_default_check.isChecked() and spectro_mode == 1):
                window_num = 10
                self.read_ref_default()
                self.sgProcess(refSpectro_data)
                self.smdBtn_checkable()
            elif(self.Spectro_btn.text() == "Stop"):
                self.continuous_check.setChecked(False)
            else:
                bo_mode = 0
                window_num = 3  
                paracheck = self.spectroPara_check()                 # 判斷有無缺漏參數 沒有缺漏 return 1
                if(paracheck == 1):
                    self.Dark_btn.setEnabled(False)
                    self.Spectro_btn.setEnabled(False)
                    t_button_check = 0
                    thread4 = threading.Thread(target = thread_4,args = (window_num,))
                    thread4.start()
        except Exception as e:
            print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e))
            return 0    
        
    def smd(self):
        global refsmd_data,samsmd_data,t_button_check,spectro_mode,bo_mode,window_num
        try:
            spectro_mode = self.spectroMode_check()
            if(self.Smd_btn.text() == "Stop"):
                self.continuous_check.setChecked(False)           
            elif(self.continuous_check.isChecked()):
                bo_mode = 0
                window_num = 5
                t_button_check = 0
                thread4 = threading.Thread(target = thread_4,args = (window_num,))
                thread4.start()
            else:
                window_num = 10
                if(spectro_mode == 1):
                    refsmd_data = refSpectro_data - Dark_data
                    self.sgProcess(refsmd_data)
                    self.statusbar.showMessage("已取得參考減暗光譜")
                else:
                    samsmd_data = sampleSpectro_data - Dark_data
                    self.sgProcess(samsmd_data)
                    self.statusbar.showMessage("已取得樣品減暗光譜")
                self.smdmbBtn_checkable()
        except Exception as e:
            print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e))
            return 0

    def smdmb(self):
        global refmall_data,sammall_data,bo_mode,t_button_check,window_num,spectro_mode
        base_data = 0
        try:
            spectro_mode = self.spectroMode_check()        
            if(self.Smdmb_btn.text() == "Stop"):
                self.continuous_check.setChecked(False)           
            elif(self.continuous_check.isChecked()):
                bo_mode = 0
                window_num = 6
                t_button_check = 0
                thread4 = threading.Thread(target = thread_4,args = (window_num,))
                thread4.start()
            else:
                window_num = 10
                if(spectro_mode == 1):
                    base_data = self.cal_baseData(refSpectro_data)
                    refmall_data = refsmd_data - base_data
                    self.sgProcess(refmall_data)
                    self.statusbar.showMessage("已取得參考減暗減基線光譜")
                else:
                    base_data = self.cal_baseData(sampleSpectro_data)
                    sammall_data = samsmd_data - base_data
                    self.sgProcess(sammall_data)
                    self.statusbar.showMessage("已取得樣品減暗減基線光譜")
            self.transBtn_checkable()
        except Exception as e:
            print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e))
        
    def trans(self):
        global trans_data,bo_mode,t_button_check,window_num
        try:
            if(self.Trans_btn.text() == "Stop"):
                self.t_continuous_check.setChecked(False)
            elif(self.t_continuous_check.isChecked()):
                bo_mode = 0
                window_num = 7
                t_button_check = 0
                thread4 = threading.Thread(target = thread_4,args = (window_num,))
                thread4.start()
            else:
                trans_data = sammall_data / refmall_data
                self.transData2spectro(trans_data)
                self.statusbar.showMessage("已取得穿透光譜")

        except Exception as e:
            print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e))

    def cal_baseData(self,data):
        base_data = 0
        try:           
            if(self.baseLineMin.text() == "" and self.baseLineMax.text() == ""):
                self.baseLineMin.setText("800")
                self.baseLineMax.setText("850")
            i = int(self.baseLineMin.text())
            j = int(self.baseLineMax.text())
            npd_lambda = np.array(d_lambda).astype(int)
            values = np.array([i,j])
            sorter = np.argsort(npd_lambda)
            sorter = sorter[np.searchsorted(npd_lambda,values,sorter = sorter)]
            s_lambda = np.array(data[sorter[0]:sorter[1]])
            base_data = np.average(s_lambda)
            return base_data
        except Exception as e:
            print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e))

    def img2spectro_garph1(self,readimg):
        global d_lambda
        self.spectro_graph.clear()
        d_lambda.clear()
        try:
            for i in range(len(readimg)):
                d_lambda.append((-1.557*10**-8*(i**3))+(4.386*10**-5*(i**2))+(0.63*i)+ 295.853) 
            self.spectro_graph.plot(d_lambda,readimg,pen=pg.mkPen('k'))
        except Exception as e:
            print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e)) 

    def transData2spectro(self,readimg):
        global sg_timg
        x = []
        sg_timg = readimg
        self.transmission_graph.clear()
        try:
            sg_mode = self.sgMode_check()
            if(sg_mode == 1):
                readimg = signal.savgol_filter(readimg,int(self.SgPoint_lineEdit.text()),int(self.SgOrder_lineEdit.text()))
                
            for i in range(len(readimg)):
                x.append((-1.557*10**-8*(i**3))+(4.386*10**-5*(i**2))+(0.63*i)+ 295.853) 
            self.transmission_graph.plot(x,readimg,pen=pg.mkPen('k'))
        except Exception as e:
            print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e)) 

    def sgProcess(self,ram_img):
        global sg_img
        sg_img = ram_img
        sg_mode = self.sgMode_check() 
        try:
            self.sgPara_check()
            if(sg_mode == 1):
                ram_img = signal.savgol_filter(ram_img,int(self.SgPoint_lineEdit.text()),int(self.SgOrder_lineEdit.text()))
                self.img2spectro_garph1(ram_img)
            else:
                self.img2spectro_garph1(ram_img)
        except Exception as e:
            print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e)) 

    def darkPara_check(self):
        check = 0
        try:
            # if(self.MachineNum_lineEdit.text() != ""):
            #     check = 1
            # else:
            #     self.statusbar.showMessage("缺少機台編號")
            if(check == 0):
                if(self.shutter_lineEdit.text() == "" or self.AnalogGain_lineEdit.text() == "" or self.DigitalGain_lineEdit.text() == ""):
                    check = 0
                    self.statusbar.showMessage("缺少相機參數")
                else:
                    check = 1
            if(check == 1):
                if(self.databox.currentText() == "none"):
                    check = 0
                    self.statusbar.showMessage("機台未連接")
            if(check == 1):
                if(self.nos_lineEdit.text() == ""):
                    check = 0
                    self.statusbar.showMessage("缺少 nos 參數")

            return check
        except Exception as e:
            print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e)) 

    def spectroPara_check(self):
        check = 0
        try:
            # if(self.MachineNum_lineEdit.text() != ""):
            #     check = 1
            # else:
            #     self.statusbar.showMessage("缺少機台編號")

            if(check == 0):
                if(self.LightA_check.isChecked() or self.LightB_check.isChecked() or self.LightC_check.isChecked()):
                    check = 1
                else:
                    check = 0
                    self.statusbar.showMessage("缺少燈源")
            if(check == 1):
                if(self.portbox.currentText() == "none"):
                    check = 0
                    self.statusbar.showMessage("機台未連接")
            if(check == 1):
                if(self.shutter_lineEdit.text() == "" or self.AnalogGain_lineEdit.text() == "" or self.DigitalGain_lineEdit.text() == ""):
                    check = 0
                    self.statusbar.showMessage("缺少相機參數")

            if(check == 1):
                if(self.nos_lineEdit.text() == ""):
                    check = 0
                    self.statusbar.showMessage("缺少 nos 參數")

            if(check == 1):
                if(self.t1_lineEdit.text() == "" and self.t2_lineEdit.text() == ""):
                    check = 0
                    self.statusbar.showMessage("缺少時間參數")
            return check
        except Exception as e:
            print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e)) 

    def Continuous_check(self):
        if(self.continuous_check.isChecked()):
            self.ref_default_check.setEnabled(False)
            if(t_button_check == 0):
                self.Smd_btn.setEnabled(False)
                self.Smdmb_btn.setEnabled(False)
            else:
                self.smdBtn_checkable()
                self.smdmbBtn_checkable()
        else:
            self.ref_default_check.setEnabled(True)

    def t_Continuous_check(self):
        if(self.t_continuous_check.isChecked()):
            if(t_button_check == 0):
                self.Trans_btn.setEnabled(False)
            
    def Ref_default_check(self):
        if(self.ref_default_check.isChecked()):
            self.continuous_check.setEnabled(False)
        else:
            self.continuous_check.setEnabled(True)           

    def light_choose(self):
        if(self.LightA_check.isChecked()):
            light = "$SLD0,"
        if(self.LightB_check.isChecked()):
            light = "$SLD1,"
        if(self.LightC_check.isChecked()):
            light = "$SLD2,"
        return light

    def ref_check(self):
        if(self.Ref_check.isChecked()):
            self.Sample_check.setChecked(False)
            self.nos_lineEdit.setEnabled(True)
            self.baseLineMin.setEnabled(True)
            self.baseLineMax.setEnabled(True)
            self.ref_default_check.setEnabled(True)
            self.continuous_check.setEnabled(True)
            self.smdBtn_checkable()                       # 判斷是否開啟 smd button  
            self.smdmbBtn_checkable()                     # 判斷是否開啟 smdmb button 
            if(t_button_check == 1):
                self.Dark_btn.setEnabled(True)
                self.Spectro_btn.setEnabled(True)
            if(self.sg_check):
                self.sgProcess(refSpectro_data)
            else:
                self.img2spectro_garph1(refSpectro_data)
        else:
            self.nos_lineEdit.setEnabled(False)
            self.baseLineMin.setEnabled(False)
            self.baseLineMax.setEnabled(False)
            self.Dark_btn.setEnabled(False)
            self.Spectro_btn.setEnabled(False)
            self.Smd_btn.setEnabled(False)
            self.Smdmb_btn.setEnabled(False)

    def sample_check(self):
        if(self.Sample_check.isChecked()):
            self.Ref_check.setChecked(False)
            self.nos_lineEdit.setEnabled(True)
            self.ref_default_check.setEnabled(True)
            self.continuous_check.setEnabled(True)
            self.baseLineMin.setEnabled(True)
            self.baseLineMax.setEnabled(True)
            self.smdBtn_checkable()
            self.smdmbBtn_checkable()
            if(t_button_check == 1):
                self.Dark_btn.setEnabled(True)
                self.Spectro_btn.setEnabled(True)
            if(self.sg_check):
                self.sgProcess(sampleSpectro_data)
            else:
                self.img2spectro_garph1(sampleSpectro_data)
        else:
            self.nos_lineEdit.setEnabled(False)
            self.baseLineMin.setEnabled(False)
            self.baseLineMax.setEnabled(False)
            self.Dark_btn.setEnabled(False)
            self.Spectro_btn.setEnabled(False)
            self.Smd_btn.setEnabled(False)
            self.Smdmb_btn.setEnabled(False)
        
    def spectroMode_check(self):
        if(self.Ref_check.isChecked()):
            return 1
        else:
            return 2
        
    def SG_check(self):
        if(len(sg_img) != 0):
            self.sgProcess(sg_img)
        if(len(sg_timg) != 0):
            self.transData2spectro(sg_timg)
        

    def sg_check(self):
        if(self.Sg_check.isChecked()):
            self.SgOrder_lineEdit.setEnabled(True)
            self.SgPoint_lineEdit.setEnabled(True)
        else:
            self.SgOrder_lineEdit.setEnabled(False)
            self.SgPoint_lineEdit.setEnabled(False)

    def sgMode_check(self):
        if(self.Sg_check.isChecked()):
            return 1
        else:
            return 0
        
    def sgPara_check(self):
        if(self.SgPoint_lineEdit.text() == '' and self.SgOrder_lineEdit.text() == ''):
            self.SgPoint_lineEdit.setText('5')
            self.SgOrder_lineEdit.setText('2')     
    
    def smdBtn_checkable(self):                                 # 判斷是否有暗光譜及光譜的資料 均有才能啟動 smd_button
        check = self.spectroMode_check()
        if(check == 1):
            if(len(Dark_data) != 0 and len(refSpectro_data) != 0):
                self.Smd_btn.setEnabled(True)
            else:
                self.Smd_btn.setEnabled(False)
        else:
            if(len(Dark_data) != 0 and len(sampleSpectro_data) != 0):
                self.Smd_btn.setEnabled(True)
            else:
                self.Smd_btn.setEnabled(False)

    def smdmbBtn_checkable(self):                              # 判斷是否有光譜減光譜的資料 有才能啟動 smdmb_button
        check = self.spectroMode_check()
        if(check == 1):
            if(len(refsmd_data) != 0):
                self.Smdmb_btn.setEnabled(True)
            else:
                self.Smdmb_btn.setEnabled(False)
        else:
            if(len(samsmd_data) != 0):
                self.Smdmb_btn.setEnabled(True)
            else:
                self.Smdmb_btn.setEnabled(False)
    
    def transBtn_checkable(self):
        if(len(refmall_data) != 0 and len(sammall_data) != 0):
            self.Trans_btn.setEnabled(True)
            self.t_continuous_check.setEnabled(True)
        else:
            self.Trans_btn.setEnabled(False)
            self.t_continuous_check.setEnabled(False)

    def save_data_ckeck(self):
        if(self.databox.currentText() == 'Ref Default'):
            self.saveData_btn.setEnabled(True)
            self.Browse_btn.setEnabled(False)
            self.SaveFName_lineEdit.setEnabled(False)
            self.BrowsePath_lineEdit.setEnabled(False)

        elif(self.SaveRaw_check.isChecked() or self.SaveSg_check.isChecked() or self.databox.currentText() == 'All'):
            self.saveData_btn.setEnabled(True)
            self.Browse_btn.setEnabled(True)
            self.BrowsePath_lineEdit.setEnabled(True)
            self.SaveFName_lineEdit.setEnabled(True)
        elif(self.SaveRaw_check.isChecked() == False and self.SaveSg_check.isChecked() == False):
            self.saveData_btn.setEnabled(False)
            self.Browse_btn.setEnabled(False)
            self.BrowsePath_lineEdit.setEnabled(False)
            self.SaveFName_lineEdit.setEnabled(False)

    def y_axis_clicked_t(self):
        if self.Graph1_yYfix.isChecked():
            yaxis_min = self.Graph1_Ymin.text()
            yaxis_max = self.Graph1_Ymax.text() 
            self.spectro_graph.setYRange(float(yaxis_min),float(yaxis_max),padding = 0)
            self.Graph1_Ymin.setEnabled(True)
            self.Graph1_Ymax.setEnabled(True)
        elif self.Graph1_Yauto.isChecked():
            self.spectro_graph.enableAutoRange(axis = 'y')
            self.Graph1_Ymin.setEnabled(False)
            self.Graph1_Ymax.setEnabled(False)

    def x_axis_clicked_t(self):
        if self.Graph1_Xfix.isChecked():
            xaxis_min = self.Graph1_Xmin.text()
            xaxis_max = self.Graph1_Xmax.text()
            self.spectro_graph.setXRange(float(xaxis_min),float(xaxis_max),padding = 0)
            self.Graph1_Xmin.setEnabled(True)
            self.Graph1_Xmax.setEnabled(True)
            
        elif self.Graph1_Xauto.isChecked():
            self.spectro_graph.enableAutoRange(axis = 'x')
            self.Graph1_Xmin.setEnabled(False)
            self.Graph1_Xmax.setEnabled(False)
    
    def y_axis_fix_t(self):
        yaxis_min = self.Graph1_Ymin.text()
        yaxis_max = self.Graph1_Ymax.text()
        self.spectro_graph.setYRange(float(yaxis_min),float(yaxis_max),padding = 0)
    
    def x_axis_fix_t(self):
        xaxis_min = self.Graph1_Xmin.text()
        xaxis_max = self.Graph1_Xmax.text()
        self.spectro_graph.setXRange(float(xaxis_min),float(xaxis_max),padding = 0)
 
    def y_axis2_clicked_t(self):
        if self.Graph2_Yfix.isChecked():
            yaxis_min = self.Graph2_Ymin.text()
            yaxis_max = self.Graph2_Ymax.text() 
            self.transmission_graph.setYRange(float(yaxis_min),float(yaxis_max),padding = 0)
            self.Graph2_Ymin.setEnabled(True)
            self.Graph2_Ymax.setEnabled(True)
        elif self.Graph2_Yauto.isChecked():
            self.transmission_graph.enableAutoRange(axis = 'y')
            self.Graph2_Ymin.setEnabled(False)
            self.Graph2_Ymax.setEnabled(False)

    def x_axis2_clicked_t(self):
        if self.Graph2_Xfix.isChecked():
            xaxis_min = self.Graph2_Xmin.text()
            xaxis_max = self.Graph2_Xmax.text()
            self.transmission_graph.setXRange(float(xaxis_min),float(xaxis_max),padding = 0)
            self.Graph2_Xmin.setEnabled(True)
            self.Graph2_Xmax.setEnabled(True)
        elif self.Graph2_Xauto.isChecked():
            self.transmission_graph.enableAutoRange(axis = 'x')
            self.Graph2_Xmin.setEnabled(False)
            self.Graph2_Xmax.setEnabled(False)
    
    def y_axis2_fix_t(self):
        yaxis_min = self.Graph2_Ymin.text()
        yaxis_max = self.Graph2_Ymax.text()
        self.transmission_graph.setYRange(float(yaxis_min),float(yaxis_max),padding = 0)
    
    def x_axis2_fix_t(self):
        xaxis_min = self.Graph2_Xmin.text()
        xaxis_max = self.Graph2_Xmax.text()
        self.transmission_graph.setXRange(float(xaxis_min),float(xaxis_max),padding = 0)

    def draw_graph_signal(self):
        try:
            signalComm.bo_new_data.emit()
            return 1
        except Exception as e:
            print('error:{}'.format(e))
            return 0  

    def bo_update_wdata(self):
        try:
            if(window_num != 7):
                self.spectro_graph.clear()
            else:
                self.transmission_graph.clear()
            x = []
            for i in range(len(ncolmean)):
                x.append((-1.557*10**-8*(i**3))+(4.386*10**-5*(i**2))+(0.63*i)+ 295.853) 
                
            if self.Sg_check.isChecked():
                y = signal.savgol_filter(ncolmean, int(self.SgPoint_lineEdit.text()), int(self.SgOrder_lineEdit.text()))
            else:
                y = ncolmean
            if(window_num == 7):
                self.transmission_graph.plot(x,y,pen = pg.mkPen('k'))
            else:
                self.spectro_graph.plot(x,y,pen = pg.mkPen('k'))
            return 1
        except Exception as e:
            print('error:{}'.format(e))
            return 0
         
    def save_ref_default(self):
        dataframe = pd.DataFrame({'Lambda':d_lambda,'Dark':Dark_data,'Spectrum':refSpectro_data,'Smd':refsmd_data,'Smdmb':refmall_data})
        dataframe.to_csv('./ttest/ref_default.csv',index = True)
        pass

    def saveData_bo(self):
        global refSpectro_data,refsmd_data,refmall_data,Dark_data,sampleSpectro_data,samsmd_data,sammall_data,trans_data
        ram_data = []
        sp_mode = self.spectroMode_check() 
        try:
            self.statusbar.showMessage("Saving")
            path = self.SaveFName_lineEdit.text()
            dic = self.BrowsePath_lineEdit.text()
            if path == "":
                path = time.strftime("%Y%m%d_%H%M%S")
            if dic != "":
                dic += "/"
            if(self.databox.currentText() == 'Ref Default'):
                self.save_ref_default()
            if self.SaveRaw_check.isChecked():
                path_raw = dic + path + "_raw.txt"
                if(self.databox.currentText()=='Transmission'):
                        check = self.helper_save_funtion_bo(path_raw, trans_data)
                        if check != 1:
                            raise Exception
                if(sp_mode == 1):
                    if(self.databox.currentText()=='Dark'):
                        check = self.helper_save_funtion_bo(path_raw, Dark_data)
                        if check != 1:
                            raise Exception
                    elif(self.databox.currentText()=='Spectrum'):
                        check = self.helper_save_funtion_bo(path_raw, refSpectro_data)
                        if check != 1:
                            raise Exception
                    elif(self.databox.currentText()=='S - D'):
                        check = self.helper_save_funtion_bo(path_raw, refsmd_data)
                        if check != 1:
                            raise Exception
                    elif(self.databox.currentText()=='S - D - B'):
                        check = self.helper_save_funtion_bo(path_raw, refmall_data)
                        if check != 1:
                            raise Exception
                else:
                    if(self.databox.currentText()=='Dark'):
                        check = self.helper_save_funtion_bo(path_raw, Dark_data)
                        if check != 1:
                            raise Exception
                    elif(self.databox.currentText()=='Spectrum'):
                        check = self.helper_save_funtion_bo(path_raw, sampleSpectro_data)
                        if check != 1:
                            raise Exception
                    elif(self.databox.currentText()=='S - D'):
                        check = self.helper_save_funtion_bo(path_raw, samsmd_data)
                        if check != 1:
                            raise Exception
                    elif(self.databox.currentText()=='S - D - B'):
                        check = self.helper_save_funtion_bo(path_raw, sammall_data)
                        if check != 1:
                            raise Exception
            if self.SaveSg_check.isChecked():
                path_sg = dic + path + "_sg.txt"
                if(self.databox.currentText()=='Transmission'):
                    ram_data = signal.savgol_filter(trans_data, int(self.SgPoint_lineEdit.text()), int(self.SgOrder_lineEdit.text()))
                    check = self.helper_save_funtion_bo(path_sg, ram_data)
                    if check != 1:
                        raise Exception
                if(sp_mode == 1):
                    if(self.databox.currentText()=='Dark'):
                        ram_data = signal.savgol_filter(Dark_data, int(self.SgPoint_lineEdit.text()), int(self.SgOrder_lineEdit.text()))
                        check = self.helper_save_funtion_bo(path_sg, ram_data)
                        if check != 1:
                            raise Exception
                    elif(self.databox.currentText()=='Spectrum'):
                        ram_data = signal.savgol_filter(refSpectro_data, int(self.SgPoint_lineEdit.text()), int(self.SgOrder_lineEdit.text()))
                        check = self.helper_save_funtion_bo(path_sg, ram_data)
                        if check != 1:
                            raise Exception
                    elif(self.databox.currentText()=='S - D'):
                        ram_data = signal.savgol_filter(refsmd_data, int(self.SgPoint_lineEdit.text()), int(self.SgOrder_lineEdit.text()))
                        check = self.helper_save_funtion_bo(path_sg, ram_data)
                        if check != 1:
                            raise Exception
                    elif(self.databox.currentText()=='S - D - B'):
                        ram_data = signal.savgol_filter(refmall_data, int(self.SgPoint_lineEdit.text()), int(self.SgOrder_lineEdit.text()))
                        check = self.helper_save_funtion_bo(path_sg, ram_data)
                        if check != 1:
                            raise Exception
                else:
                    if(self.databox.currentText()=='Dark'):
                        ram_data = signal.savgol_filter(refmall_data, int(self.SgPoint_lineEdit.text()), int(self.SgOrder_lineEdit.text()))
                        check = self.helper_save_funtion_bo(path_sg, ram_data)
                        if check != 1:
                            raise Exception
                    elif(self.databox.currentText()=='Spectrum'):
                        ram_data = signal.savgol_filter(sampleSpectro_data, int(self.SgPoint_lineEdit.text()), int(self.SgOrder_lineEdit.text()))
                        check = self.helper_save_funtion_bo(path_sg, ram_data)
                        if check != 1:
                            raise Exception
                    elif(self.databox.currentText()=='S - D'):
                        ram_data = signal.savgol_filter(samsmd_data, int(self.SgPoint_lineEdit.text()), int(self.SgOrder_lineEdit.text()))
                        check = self.helper_save_funtion_bo(path_sg, ram_data)
                        if check != 1:
                            raise Exception
                    elif(self.databox.currentText()=='S - D - B'):
                        ram_data = signal.savgol_filter(sammall_data, int(self.SgPoint_lineEdit.text()), int(self.SgOrder_lineEdit.text()))
                        check = self.helper_save_funtion_bo(path_sg, ram_data)
                        if check != 1:
                            raise Exception
            if(self.databox.currentText()=='All'):
                self.sgPara_check()
                path = self.SaveFName_lineEdit.text()
                dic = self.BrowsePath_lineEdit.text()
                if path == "":
                    path = time.strftime("%Y%m%d_%H%M%S")
                if dic != "":
                    dic += "/"
                folder_path = dic + path                 #創立資料夾
                os.mkdir(folder_path)
                path = '{}/Dark_raw.txt'.format(folder_path)
                check = self.helper_save_funtion_bo(path, Dark_data)
                if check != 1:
                    raise Exception
                path = '{}/ref_Spectrum_raw.txt'.format(folder_path)
                check = self.helper_save_funtion_bo(path, refSpectro_data)
                if check != 1:
                    raise Exception
                path = '{}/ref_Smd_raw.txt'.format(folder_path)
                check = self.helper_save_funtion_bo(path, refsmd_data)
                if check != 1:
                    raise Exception
                path = '{}/ref_Smdmb_raw.txt'.format(folder_path)
                check = self.helper_save_funtion_bo(path, refmall_data)
                if check != 1:
                    raise Exception
                path = '{}/sam_Spectrum_raw.txt'.format(folder_path)
                check = self.helper_save_funtion_bo(path, sampleSpectro_data)
                if check != 1:
                    raise Exception
                path = '{}/sam_Smd_raw.txt'.format(folder_path)
                check = self.helper_save_funtion_bo(path, samsmd_data)
                if check != 1:
                    raise Exception
                path = '{}/sam_Smdmb_raw.txt'.format(folder_path)
                check = self.helper_save_funtion_bo(path, sammall_data)
                if check != 1:
                    raise Exception
                path = '{}/Transmission_raw.txt'.format(folder_path)
                check = self.helper_save_funtion_bo(path, trans_data)

                path = '{}/Dark_sg.txt'.format(folder_path)
                ram_data = signal.savgol_filter(Dark_data, int(self.SgPoint_lineEdit.text()), int(self.SgOrder_lineEdit.text()))
                check = self.helper_save_funtion_bo(path, ram_data)
                if check != 1:
                    raise Exception
                path = '{}/ref_Spectrum_sg.txt'.format(folder_path)
                ram_data = signal.savgol_filter(refSpectro_data, int(self.SgPoint_lineEdit.text()), int(self.SgOrder_lineEdit.text()))
                check = self.helper_save_funtion_bo(path, ram_data)
                if check != 1:
                    raise Exception
                path = '{}/ref_Smd_sg.txt'.format(folder_path)
                ram_data = signal.savgol_filter(refsmd_data, int(self.SgPoint_lineEdit.text()), int(self.SgOrder_lineEdit.text()))
                check = self.helper_save_funtion_bo(path, ram_data)
                if check != 1:
                    raise Exception
                path = '{}/ref_Smdmb_sg.txt'.format(folder_path)
                ram_data = signal.savgol_filter(refmall_data, int(self.SgPoint_lineEdit.text()), int(self.SgOrder_lineEdit.text()))
                check = self.helper_save_funtion_bo(path, ram_data)
                if check != 1:
                    raise Exception
                ram_data = signal.savgol_filter(sampleSpectro_data, int(self.SgPoint_lineEdit.text()), int(self.SgOrder_lineEdit.text()))
                check = self.helper_save_funtion_bo(path, ram_data)
                if check != 1:
                    raise Exception
                path = '{}/sam_Smd_sg.txt'.format(folder_path)
                ram_data = signal.savgol_filter(samsmd_data, int(self.SgPoint_lineEdit.text()), int(self.SgOrder_lineEdit.text()))
                check = self.helper_save_funtion_bo(path, ram_data)
                if check != 1:
                    raise Exception
                path = '{}/sam_Smdmb_sg.txt'.format(folder_path)
                ram_data = signal.savgol_filter(sammall_data, int(self.SgPoint_lineEdit.text()), int(self.SgOrder_lineEdit.text()))
                check = self.helper_save_funtion_bo(path, ram_data)
                if check != 1:
                    raise Exception
                path = '{}/Transmission_sg.txt'.format(folder_path)
                ram_data = signal.savgol_filter(trans_data, int(self.SgPoint_lineEdit.text()), int(self.SgOrder_lineEdit.text()))
                check = self.helper_save_funtion_bo(path, ram_data)
                if check != 1:
                    raise Exception
            print("Save Complete")
            self.statusbar.showMessage("Save Complete")
            
        except Exception as e:
            print('error:{}'.format(e))
            print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e))
            self.statusbar.showMessage("Save Error")			

    def browse_path_bo(self):
        filename = QtWidgets.QFileDialog.getExistingDirectory(None, 'Save Path', '')
        self.BrowsePath_lineEdit.setText(filename)

    def helper_save_funtion_bo(self, path, data):
        try:
            f = open(path, 'w')
            for i in data:
                f.write(str(i) + "\n")
            f.close()
            return 1
        except Exception as e:
            print('error:{}'.format(e))
        return 0
    
    def read_ref_default(self):
        global d_lambda,Dark_data,refSpectro_data
        try:
            ref_default = pd.read_csv('./ttest/ref_default.csv')
            Dark_data = ref_default.iloc[:,2].to_numpy()
            refSpectro_data = ref_default.iloc[:,3].to_numpy()
        except FileNotFoundError:
            print('No default file')
                 
    def refresh_com(self):
        self.portbox.clear()
        self.portbox.setCurrentIndex(1)
        self.portbox.addItem("none")
        portNames = [
            "/dev/ttyUSB0",
            "/dev/ttyUSB1",
            "/dev/ttyUSB2",
            "/dev/ttyUSB3",
            "/dev/ttyACM0",
            "/dev/ttyACM1",
            "/dev/ttyACM2",
            "/dev/ttyACM3"
        ]
        for pname in portNames:
            try:
                ser.port = pname
                ser.open()
                if ser.isOpen():
                    print("Found {}.".format(pname))
                    self.portbox.addItem(pname)
                ser.close()
            except:
                pass

# 拍照
def takephoto():
    try:
        imgformat = ui.format_box.currentText().lower()
        if window_num == 1:
            shutter = ui.shutter_edit.text()
            anolog_gain = ui.anologgain_edit.text()
            digital_gain = ui.digitalgain_edit.text()
            imgname = "./ttest/test.{}".format(imgformat)
        else:
            shutter = t_ui.shutter_lineEdit.text()
            anolog_gain = t_ui.AnalogGain_lineEdit.text()
            digital_gain = t_ui.DigitalGain_lineEdit.text()
            imgname = "./ttest/test.{}".format(imgformat)
        
        subprocess.run(["libcamera-still", "--shutter", shutter, "--analoggain", anolog_gain, "-o", imgname,"--immediate","--nopreview"])
        return 1
    except Exception as e:
        print('error:{}'.format(e))
        return 0    
    
# 取 roi 並轉成光譜 
def crop_image():
    global data, max_value
    try:
        imgformat = ui.format_box.currentText().lower()
        sImagePath = "./ttest/test.{}".format(imgformat)
        
        x = int(ui.x0.text())
        y = int(ui.y0.text())
        deltax = int(ui.x1.text())
        deltay = int(ui.y1.text())
        
        nImage = cv2.imread(sImagePath, cv2.IMREAD_GRAYSCALE)
        nCrop_Img = nImage[y:y+deltay, x:x+deltax]

        nColMean = np.mean(nCrop_Img, axis = 0)
        nImgColMean = nColMean.reshape(1, len(nColMean))
        
        data = nImgColMean[0]
        
        a = np.argmax(data)
        max_value = data[a]
        return 1        
    except Exception as e:
        print('error:{}'.format(e))
        return None 
    
# auto roi 
def sum_image():
    global new_y0
    try:
        deltay = int(ui.y1.text())
        imgformat = ui.format_box.currentText().lower()
        sImagePath = "./ttest/test.{}".format(imgformat)
        nImage = cv2.imread(sImagePath, cv2.IMREAD_GRAYSCALE)
        nRowSum = np.sum(nImage, axis = 1)
        a = np.argmax(nRowSum)
        new_y0 = a-deltay/2
        if new_y0 <= 0:
            new_y0 = 0
        signalComm.new_y0.emit()
        return 1
    except Exception as e:
        print('error:{}'.format(e))
        return 0
    
# 波長轉換
def wavelength_convert():
    global wdata
    wdata.clear()
    try:
        a3 = float(ui.a3.text())*10**(float(ui.e3.text()))
        a2 = float(ui.a2.text())*10**(float(ui.e2.text()))
        a1 = float(ui.a1.text())*10**(float(ui.e1.text()))
        a0 = float(ui.a0.text())*10**(float(ui.e0.text()))
        
        for i in range(len(data)):
            wdata.append((a3*(i**3))+(a2*(i**2))+(a1*i)+ a0)
        return 1
    except Exception as e:
        print('error:{}'.format(e))
        return 0
    
# autoscaling 
def checkluminous():
    try:
        global goal_st
        if window_num == 1:
            sh = int(ui.shutter_edit.text())
        else:
            sh = int(t_ui.shutter_lineEdit.text())

        if(sh>=st_max):
            goal_st = st_max
            signalComm.new_goal_st.emit()
            return '5'
        if (max_value >= I_max):
            return '0'
        elif (max_value > I_thr_top):
            return '1'
        elif (max_value < I_thr_top and max_value > I_thr_bottom):
            return '2'
        elif (max_value < I_thr_bottom /2):
            return '4'
        elif (max_value < I_thr_bottom):
            return '3'
    except Exception as e:
        raise Exception("Check Error")
        #print('error:{}'.format(e))
        #return 0
    
    # autoscaling 調整 shutter / 2
def set_half_exp():
    global st1, I1
    try:
        if window_num == 1:
            st1 = float(ui.shutter_edit.text())
            I1 = max_value
            st = int(ui.shutter_edit.text())
            ui.shutter_edit.setText(str(int(st/2)))
        else:
            st1 = float(t_ui.shutter_lineEdit.text())
            I1 = max_value
            st = int(t_ui.shutter_lineEdit.text())
            t_ui.shutter_lineEdit.setText(str(int(st/2)))
        return 1
    except Exception as e:
        print('error:{}'.format(e))
        return 0
    
    # autoscaling 調整 shutter * 2
def set_double_exp():
    global st1, I1
    try:
        if window_num == 1:
            st1 = float(ui.shutter_edit.text())
            I1 = max_value
            
            st = int(ui.shutter_edit.text())
            ui.shutter_edit.setText(str(int(st*2)))
        else:
            st1 = float(t_ui.shutter_lineEdit.text())
            I1 = max_value
            
            st = int(t_ui.shutter_lineEdit.text())
            t_ui.shutter_lineEdit.setText(str(int(st*2)))
        return 1
    except Exception as e:
        print('error:{}'.format(e))
        return 0
    
    # autoscaling peak 確認
def find_target_exp():
    global goal_st
    try:
        c = '1'
        if window_num == 1:
            st2 = float(ui.shutter_edit.text())
        else:
            st2 = float(t_ui.shutter_lineEdit.text())

        I2 = max_value
        
        goal_st = int(st1 + ((st1 - st2)/(I1 - I2) * (I_thr - I1)))
        if goal_st >= st_max:
            print("Light too Weak")
            goal_st = st_max
            c = '2'
        elif goal_st < 0:
            print("Light too Strong")
            goal_st = shutter
            c = '3'
            
        signalComm.new_goal_st.emit()
        return c
    except Exception as e:
        goal_st = shutter
        signalComm.new_goal_st.emit()
        print('error:{}'.format(e))
        return 0

def number_ofscan():
    global numb_ofscan
    try:
        numb_ofscan.append(data)
        return 1
    except Exception as e:
        print('error:{}'.format(e))
        return 0

def cal_number_ofscan():
    global ncolmean,sg_img,sg_timg
    try:
        ncolmean = np.mean(np.asarray(numb_ofscan), axis = 0)
        if(window_num == 5):
            ncolmean = ncolmean - Dark_data
        elif(window_num == 6):
            basedata = t_ui.cal_baseData(ncolmean)
            ncolmean = ncolmean - basedata
        sg_img = ncolmean
        if(window_num == 7):
            basedata = t_ui.cal_baseData(ncolmean)
            ncolmean = (ncolmean - Dark_data - basedata) / refmall_data
            sg_timg = ncolmean
        return 1
    except Exception as e:
        print('error:{}'.format(e))
        return 0

def find_hgar_dividerpoint():
    try:
        global hg_max, hg_data, hg_peak, ar_data, ar_peak, dist
        
        yData = ncolmean
        
        y_smooth = signal.savgol_filter(yData, window_length = 21, polyorder = 3)

        peaks, _ = signal.find_peaks(y_smooth, height = 0)
        p_peaks = y_smooth[peaks]
        p_peaks = p_peaks.tolist()

        p_peaksmax_index1 = p_peaks.index(max(p_peaks))
        p_peaksmax1 = peaks[p_peaksmax_index1]
        p_peaks.pop(p_peaksmax_index1)

        p_peaksmax_index2 = p_peaks.index(max(p_peaks))
        p_peaksmax2 = peaks[p_peaksmax_index2]

        if p_peaksmax1 > p_peaksmax2:
            dist = p_peaksmax1 - p_peaksmax2
            hg_max = p_peaksmax1 + dist
        elif p_peaksmax1 < p_peaksmax2:
            p_peaksmax2 = peaks[p_peaksmax_index2 + 1]
            dist = p_peaksmax2 - p_peaksmax1
            hg_max = p_peaksmax2 + dist
        
        for i in peaks:
            if i < hg_max:
                hg_peak.append(i)
            else:
                ar_peak.append(i-hg_max)

        hg_data = y_smooth[:hg_max]
        ar_data = y_smooth[hg_max:]

        return 1
    except Exception as e:
        print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e))
        return 0

def find_hg_peaks():
    try:
        global hg_peaks
        
        hg_pdata = hg_data[hg_peak].tolist()
        hg_peak1 = []
        while len(hg_peak1) < 5:
            maxpos = hg_pdata.index(max(hg_pdata))
            hg_peak1.append(hg_peak[maxpos])
            hg_peak.pop(maxpos)
            hg_pdata.pop(maxpos)

        hg_peak1.sort()
        
        for i in range(len(hg_peak1)):
            if i > 0 and i < 4:
                hg_peaks.append(hg_peak1[i])
        return 1
    except Exception as e:
        print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e))
        return 0

def find_ar_peaks():
    try:
        global ar_peaks, hg_max
        
        hg_max = hg_max + 1
        
        ar_pdata = ar_data[ar_peak].tolist()
        ar_q1_peak = []
        ar_q2_peak = []
        ar_q3_peak = []
        
        #find q2 peak
        maxpos = ar_pdata.index(max(ar_pdata))
        ar_peaks.append(ar_peak[maxpos] + hg_max)
        
        #find q1 peak
        ar_q1 = (ar_peak[maxpos])/2

        for i in ar_peak:
            if i < ar_q1:
                ar_q1_peak.append(i)
                
        ar_q1_peaks = ar_data[ar_q1_peak].tolist()
        q1_peak = ar_q1_peaks.index(max(ar_q1_peaks))
        ar_peaks.append(ar_peak[q1_peak] + hg_max)
        
        #find q3 peak
        ar_q3 = ar_peak[maxpos] + dist
        
        for i in ar_peak:
            if i > ar_q3:
                ar_q3_peak.append(i)
                
        q3_pos = (len(ar_peak)) - (len(ar_q3_peak))       
        ar_q3_peaks = ar_data[ar_q3_peak].tolist()
        q3_peak = ar_q3_peaks.index(max(ar_q3_peaks))
        ar_peaks.append(ar_peak[q3_peak + q3_pos] + hg_max)
        
        #find q2 peak
        ar_q2 = dist * 1.1
        
        for i in ar_peak:
            if i > ar_q2 and i < ar_q3:
                ar_q2_peak.append(i)
                
        q2_pos = (len(ar_peak) - len(ar_q2_peak) - len(ar_q3_peak))       
        ar_q2_peaks = ar_data[ar_q2_peak].tolist()
        q2_peak = ar_q2_peaks.index(max(ar_q2_peaks))
        ar_peaks.append(ar_peak[q2_peak + q2_pos] + hg_max)
        ar_peaks.sort()
        
        return 1
    except Exception as e:
        print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e))
        return 0
    
def savedatas(img):
    global Dark_data,refSpectro_data,sampleSpectro_data,refsmd_data,samsmd_data,refsmall_data,sammall_data,trans_data
    try:
        if window_num == 4:
            Dark_data = img
        elif window_num == 3:                    # 參考或取樣光譜
            if spectro_mode == 1:                   # 參考
                refSpectro_data = img
            else:
                sampleSpectro_data = img
        elif window_num == 5:
            if spectro_mode == 1:
                refsmd_data = img
            else:
                samsmd_data = img
        elif window_num == 6:
            if spectro_mode == 1:
                refsmall_data = img
            else:
                sammall_data = img
        elif window_num == 7:
            trans_data = img
        return 1
    except Exception as e:
        print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e))
        return 0

def close_light_helper():
    global t_button_check
    #if window_num == 3 or window_num == 4:
    t_ui.smdBtn_checkable()
    t_ui.smdmbBtn_checkable()
    t_ui.transBtn_checkable()
    if window_num != 4:
        time.sleep(int(t_ui.t2_lineEdit.text()))
    t_button_check = 1

    if (t_ui.Ref_check.isChecked() or t_ui.Sample_check.isChecked()):
        t_ui.Spectro_btn.setEnabled(True)
        t_ui.Dark_btn.setEnabled(True)
        if(t_ui.continuous_check.isChecked()):
            t_ui.Smd_btn.setEnabled(True)
            t_ui.Smdmb_btn.setEnabled(True)
    if(t_ui.t_continuous_check.isChecked()):
        t_ui.Trans_btn.setEnabled(True)
        
def btnEnable_check():
    _translate = QtCore.QCoreApplication.translate
    if window_num == 4:
        t_ui.Dark_btn.setText(_translate("Transmission_Window", "Stop"))
        t_ui.Spectro_btn.setEnabled(False)
        t_ui.Smd_btn.setEnabled(False)
        t_ui.Smdmb_btn.setEnabled(False)
    elif window_num == 3:
        t_ui.Spectro_btn.setEnabled(True)
        t_ui.Spectro_btn.setText(_translate("Transmission_Window", "Stop"))
        t_ui.Dark_btn.setEnabled(False)
        t_ui.Smd_btn.setEnabled(False)
        t_ui.Smdmb_btn.setEnabled(False)
    elif window_num == 5:
        t_ui.Smd_btn.setEnabled(True)
        t_ui.Smd_btn.setText(_translate("Transmission_Window", "Stop"))
        t_ui.Dark_btn.setEnabled(False)
        t_ui.Spectro_btn.setEnabled(False)
        t_ui.Smdmb_btn.setEnabled(False)
    elif window_num == 6:
        t_ui.Smdmb_btn.setEnabled(True)
        t_ui.Smdmb_btn.setText(_translate("Transmission_Window", "Stop"))
        t_ui.Dark_btn.setEnabled(False)
        t_ui.Spectro_btn.setEnabled(False)
        t_ui.Smd_btn.setEnabled(False)
    elif window_num == 7:
        t_ui.Trans_btn.setEnabled(True)
        t_ui.Trans_btn.setText(_translate("Transmission_Window", "Stop"))
        t_ui.Dark_btn.setEnabled(False)
        t_ui.Spectro_btn.setEnabled(False)
        t_ui.Smd_btn.setEnabled(False)
        t_ui.Smdmb_btn.setEnabled(False)

def continue_stop():
    _translate = QtCore.QCoreApplication.translate
    if window_num == 3:
        t_ui.Spectro_btn.setEnabled(False)
        t_ui.Spectro_btn.setText(_translate("Transmission_Window", "Start"))
    elif window_num == 4:
        t_ui.Dark_btn.setText(_translate("Transmission_Window", "Start"))
    elif window_num == 5:
        t_ui.Smd_btn.setEnabled(False)
        t_ui.Smd_btn.setText(_translate("Transmission_Window", "Start"))
    elif window_num == 6:
        t_ui.Smdmb_btn.setEnabled(False)
        t_ui.Smdmb_btn.setText(_translate("Transmission_Window", "Start"))
    elif window_num == 7:
        t_ui.Trans_btn.setEnabled(False)
        t_ui.Trans_btn.setText(_translate("Transmission_Window", "Start"))

def thread_1(): #main function
    global mode, image_mode, numb_ofscan, roi_mode, window_num
    scan_time = 0
    first_scan = 1
    ui.statusbar.showMessage("CAPTURING IMAGE")
    while True:
        if mode == 0:
            if flag == 1:
                mode = 10
                window_num = 1
            else:
                break
        elif mode == 10:
            check = takephoto()
            if check == 1:
                mode = 20
            else:
                mode = 999
        elif mode == 20:
            if first_scan == 1:
                if roi_mode == 0:
                    check = sum_image()
                    if check == 1:
                        mode = 30
                    else:
                        mode = 999
                else:
                    mode = 30
            else:
                mode = 30           
        elif mode == 30:
            check = crop_image()
            if check == 1:
                mode = 31
            else:
                mode = 999
        elif mode == 31:
            check = number_ofscan()
            if check == 1:
                first_scan = 0
                scan_time += 1
                if scan_time < int(num_scan):
                    mode = 10
                else:
                    mode = 32
            else:
                mode = 999
        elif mode == 32:
            check = cal_number_ofscan()
            if check == 1:
                mode = 40
            else:
                mode = 999
        elif mode == 40:
            check = ui.draw_spectrum_graph_signal()
            if check == 1:
                mode = 50
            else:
                mode = 999
        elif mode == 50:
            check = ui.update_image_signal()
            if check == 1:
                mode = 60
            else:
                mode = 999
        elif mode == 60:
            check = wavelength_convert()
            if check == 1:
                mode = 70
            else:
                mode = 999
        elif mode == 70:
            check = ui.draw_wavelength_graph_signal()
            if check == 1:
                numb_ofscan.clear()
                scan_time = 0
                mode = 0
            else:
                mode = 999
        elif mode == 999:
            print("Main Function Error")
            ui.statusbar.showMessage("CAPTURE IMAGE Error")
            raise Exception
        
    print("Main Function Complete")
    ui.statusbar.showMessage("CAPTURE IMAGE COMPLETE")
    
def thread_2(): #auto scaling
    global auto_mode
    t_times = 0
    first_scan = 1
    if window_num == 1:
        ui.statusbar.showMessage("AUTO SCALING")
    else:
        t_ui.statusbar.showMessage("AUTO SCALING")
        
    while True:
        if auto_mode == 0:
            check = t_ui.light_open()
            if check == 1:
                auto_mode = 10
            else:
                auto_mode = 999
        if auto_mode == 10:
            check = takephoto()
            if check == 1:
                auto_mode = 20
            else:
                auto_mode = 999
        elif auto_mode == 20:
            if first_scan == 1:
                if roi_mode == 0:
                    check = sum_image()
                    if check == 1:
                        auto_mode = 30
                        first_scan = 0
                    else:
                        auto_mode = 999
                else:
                    auto_mode = 30
            else:
                auto_mode = 30
        elif auto_mode == 30:
            check = crop_image()
            if check == 1:
                if t_times == 0:
                    auto_mode = 40
                else:
                    auto_mode = 60
            else:
                auto_mode = 999
        elif auto_mode == 40:
            check = checkluminous()
            if check == '0':    # peak(max_value) > I_max
                auto_mode = 51
            elif check == '1':  # peak(max_value) > I_thr_top
                auto_mode = 50
            elif check == '2':  # peak(max_value) is acceptable 
                auto_mode = 70
            elif check == '3':  # peak(max_value) < I_thr_buttom
                auto_mode = 55
            elif check == '4':
                auto_mode = 56
            elif check == '5':
                auto_mode = 70
            else:
                auto_mode = 999
        elif auto_mode == 50:
            check = set_half_exp()
            if check == 1:
                auto_mode = 10
                t_times = 1
            else:
                auto_mode = 999
        elif auto_mode == 51:
            check = set_half_exp()
            if check == 1:
                auto_mode = 10
            else:
                auto_mode = 999
        elif auto_mode == 55:
            check = set_double_exp()
            if check == 1:
                auto_mode = 10
                t_times = 1
            else:
                auto_mode = 999
        elif auto_mode == 56:
            check = set_double_exp()
            if check == 1:
                auto_mode = 10
            else:
                auto_mode = 999
        elif auto_mode == 60:
            check = find_target_exp()
            if check == '1':
                auto_mode = 10
                t_times = 0
            elif check == '2' or check == '3':
                auto_mode = 70
            else:
                auto_mode = 999
        elif auto_mode == 70:
            check = number_ofscan()
            if check == 1:
                auto_mode = 80
            else:
                auto_mode = 999
        elif auto_mode == 80:
            check = cal_number_ofscan()
            if check == 1:
                auto_mode = 100
            else:
                auto_mode = 999
        elif auto_mode == 100:
            if window_num == 1:
                check = ui.draw_spectrum_graph_signal()
                if check == 1:
                    auto_mode = 110
                else:
                    auto_mode = 999
            else:
                check = t_ui.draw_graph_signal()
                if check == 1:
                    auto_mode = 120
                else:
                    auto_mode = 999
        elif auto_mode == 110:
            check = ui.update_image_signal()
            if check == 1:
                break
            else:
                auto_mode = 999
        elif auto_mode == 120:
            t_ui.light_close()
            close_light_helper()
            break
        elif auto_mode == 999:
            print("Auto Scaling Error")
            if window_num == 1:
                ui.statusbar.showMessage("AUTO SCALING Error")
            else:
                t_ui.statusbar.showMessage("AUTO SCALING Error")
            raise Exception
    numb_ofscan.clear()
    print('Auto Scaling Complete')
    if window_num == 1:
        ui.statusbar.showMessage("AUTO SCALING Complete")
    else:
        t_ui.statusbar.showMessage("AUTO SCALING Complete")

def thread_3(): #auto find peak
    ui.statusbar.showMessage("FINGING PEAK")
    try: 
        global hg_peak, hg_peaks, ar_peak, ar_peaks
        
        if not isinstance(hg_peak, list):
            hg_peak = hg_peak.tolist()
        if not isinstance(hg_peaks, list):
            hg_peaks = hg_peaks.tolist()
        if not isinstance(ar_peak, list):
            ar_peak = ar_peak.tolist()
        if not isinstance(ar_peaks, list):
            ar_peaks = ar_peaks.tolist()
        
        hg_peak.clear()       
        hg_peaks.clear()
        ar_peak.clear() 
        ar_peaks.clear()
        
        check = find_hgar_dividerpoint() 
        if check != 1:
            raise Exception ("Cannot find Hg-Ar dividerpoint")
        check = find_hg_peaks()
        if check != 1:
            raise Exception ("Cannot find Hg peak")
        check = find_ar_peaks()
        if check != 1:
            raise Exception ("Cannot find Ar peak")
        signalComm.new_pixel.emit()
        ui.statusbar.showMessage("DONE")
    except Exception as e:
        print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e))
        ui.statusbar.showMessage("AUTO FIND PEAK ERROR")
        return 0
    
    # 取參考及取樣光譜
def thread_4(window_num):
    global bo_mode,numb_ofscan,ncolmean
    scan_time = 0
    ncolmean = []
    bo_num_scan = int(t_ui.nos_lineEdit.text())
    t_ui.statusbar.showMessage("CAPTURING IMAGE")
    try:
        while True:
            if bo_mode == 0:
                if t_ui.continuous_check.isChecked() or t_ui.t_continuous_check.isChecked():
                    btnEnable_check()
                bo_mode = 5
            elif bo_mode == 5:
                if window_num != 4:  
                    check = t_ui.light_open()
                    if check == 1:
                        bo_mode = 10
                    else:
                        bo_mode = 999 
                else:
                    bo_mode = 10
            elif bo_mode == 10:
                check = takephoto()
                if check == 1:
                    bo_mode = 30
                else:
                    bo_mode = 999
            elif bo_mode == 30:
                check = crop_image()
                if check == 1:
                    bo_mode = 31
                else:
                    bo_mode = 999
            elif bo_mode == 31:
                check = number_ofscan()
                if check == 1:
                    scan_time += 1
                    if scan_time < int(bo_num_scan):
                        bo_mode = 10
                    else:
                        bo_mode = 32
                else:
                    bo_mode = 999
            elif bo_mode == 32:
                check = cal_number_ofscan()
                if check == 1:
                    bo_mode = 40
                else:
                    bo_mode = 999
            elif bo_mode == 40:
                check = t_ui.draw_graph_signal()
                if check == 1:
                    bo_mode = 50
                else:
                    bo_mode = 999
            elif bo_mode == 50:
                bo_mode = 10
                numb_ofscan.clear()
                scan_time = 0
                if(window_num == 7):
                    if(not t_ui.t_continuous_check.isChecked()):
                        continue_stop()
                        bo_mode = 60
                else:
                    if not t_ui.continuous_check.isChecked():
                        continue_stop()
                        bo_mode = 60
            elif bo_mode == 60:
                check = savedatas(ncolmean)
                if check == 1:
                    if window_num != 4:
                        t_ui.light_close()
                    close_light_helper()
                    break
                else:
                    bo_mode = 999
            elif bo_mode == 999:
                print("Main Function Error")
                t_ui.statusbar.showMessage("CAPTURE IMAGE Error")
                raise Exception
        print("Main Function Complete")
        t_ui.statusbar.showMessage("CAPTURE IMAGE COMPLETE")
    except Exception as e:
        print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e))
        t_ui.statusbar.showMessage("ERROR")
        return 0

def check_dir():
    try:
        filename = "./ttest/test.txt"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
    except Exception as e:
        print("Error line: {}\nError: {}".format(e.__traceback__.tb_lineno, e))
        raise    
    
if __name__ == "__main__":
    try:       
        print("Checking...")
        app = QtWidgets.QApplication(sys.argv)
        mainwindow = QtWidgets.QMainWindow()
        secondwindow = QtWidgets.QMainWindow()
        Transmission_window = QtWidgets.QMainWindow()
        signalComm = SignalCommunication()
        ui = Ui_mainwindow()
        c_ui = Ui_w_calibration()
        t_ui = UI_Transmission_Window()
        ui.setupUi(mainwindow)
        c_ui.setupUi(secondwindow)
        t_ui.setupUi(Transmission_window)
        check_dir()
        mainwindow.show()
        sys.exit(app.exec_())
    except Exception as ex:
        print(ex)
        exit()