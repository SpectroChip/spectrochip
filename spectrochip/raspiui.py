version = "V3"

from PyQt5 import QtCore, QtGui, QtWidgets
from scipy import signal
import numpy as np
import pyqtgraph as pg
import sys, configparser, cv2, threading, subprocess

np.set_printoptions(threshold = sys.maxsize)

config = configparser.ConfigParser()
config.read('config.ini')

shutter = config['default']['shutter'] #max 1,000,000
anolog_gain = config['default']['anolog_gain'] #max 100,000,000
digital_gain = config['default']['digital_gain']
x = config['default']['x']
y = config['default']['y']
deltax = config['default']['deltax']
deltay = config['default']['deltay']
x_axis_min = config['graph']['x_axis_min']
x_axis_max = config['graph']['x_axis_max']
y_axis_min = config['graph']['y_axis_min']
y_axis_max = config['graph']['y_axis_max']

a3 = config['wavelength_calibration']['a3']
a2 = config['wavelength_calibration']['a2']
a1 = config['wavelength_calibration']['a1']
a0 = config['wavelength_calibration']['a0']
e3 = config['wavelength_calibration']['e3']
e2 = config['wavelength_calibration']['e2']
e1 = config['wavelength_calibration']['e1']
e0 = config['wavelength_calibration']['e0']

I_max = config['auto_scaling']['I_max']
I_thr_percentage = config['auto_scaling']['I_thr_percentage']
I_thr_tolerance = config['auto_scaling']['I_thr_tolerance']

num_scan = config['numof_scan']['numberof_scan']

w_length = config['sgfilter']['window_length']
poly_order = config['sgfilter']['polyorder']

st_max = 100000
ag_max = 10000000

st1 = 0
st2 = 0
I1 = 0
I2 = 0

I_thr = 0
I_thr_top = 0
I_thr_bottom = 0

mode = 0
auto_mode = 0
x_mode = 0
y_mode = 0
w_x_mode = 0
w_y_mode = 0
flag = 0
roi_mode = 1

max_value = 0
goal_st = 0
new_y0 = 0
c_draw_wgraph = 0

wdata = []
numb_ofscan = []
ncolmean = []

hg_max = 0
hg_data = []
hg_peak = []
hg_peaks = []
ar_data = []
ar_peak = []
ar_peaks = []
dist = 0

hgar_temp = [0] * 10

class SignalCommunication(QtCore.QObject):
	new_image = QtCore.pyqtSignal()
	new_y0 = QtCore.pyqtSignal()
	new_data = QtCore.pyqtSignal()
	new_wdata = QtCore.pyqtSignal()
	new_goal_st =  QtCore.pyqtSignal()
	new_pixel = QtCore.pyqtSignal()

class Ui_mainwindow(object):
	def setupUi(self, mainwindow):
		mainwindow.setObjectName("mainwindow")
		mainwindow.resize(1310, 965)
		self.centralwidget = QtWidgets.QWidget(mainwindow)
		self.centralwidget.setObjectName("centralwidget")
		
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
		
		mainwindow.setCentralWidget(self.centralwidget)
		self.menubar = QtWidgets.QMenuBar(mainwindow)
		self.menubar.setGeometry(QtCore.QRect(0, 0, 831, 21))
		self.menubar.setObjectName("menubar")
		mainwindow.setMenuBar(self.menubar)
		self.statusbar = QtWidgets.QStatusBar(mainwindow)
		self.statusbar.setObjectName("statusbar")
		mainwindow.setStatusBar(self.statusbar)
		
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
		self.pixel_list.setGeometry(QtCore.QRect(5, 615, 130, 195))
		self.pixel_list.setObjectName("pixel_list")
		self.label_6 = QtWidgets.QLabel(self.centralwidget)
		self.label_6.setGeometry(QtCore.QRect(50, 620, 100, 16))
		self.label_6.setObjectName("label_6")
		self.y_axis = QtWidgets.QPushButton(self.centralwidget)
		self.y_axis.setGeometry(QtCore.QRect(40, 680, 75, 23))
		self.y_axis.setObjectName("y_axis")
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
		self.x_axis = QtWidgets.QPushButton(self.centralwidget)
		self.x_axis.setGeometry(QtCore.QRect(40, 780, 75, 23))
		self.x_axis.setObjectName("x_axis")
		
		self.wavelength_list = QtWidgets.QListView(self.centralwidget)
		self.wavelength_list.setGeometry(QtCore.QRect(1170, 615, 130, 195))
		self.wavelength_list.setObjectName("wavelength_list")
		self.w_x_axis_label = QtWidgets.QLabel(self.centralwidget)
		self.w_x_axis_label.setGeometry(QtCore.QRect(1215, 720, 100, 16))
		self.w_x_axis_label.setObjectName("w_x_axis_label")
		self.w_x_axis = QtWidgets.QPushButton(self.centralwidget)
		self.w_x_axis.setGeometry(QtCore.QRect(1195, 780, 75, 23))
		self.w_x_axis.setObjectName("w_x_axis")
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
		self.w_y_axis = QtWidgets.QPushButton(self.centralwidget)
		self.w_y_axis.setGeometry(QtCore.QRect(1195, 680, 75, 23))
		self.w_y_axis.setObjectName("w_y_axis")
		self.label_7 = QtWidgets.QLabel(self.centralwidget)
		self.label_7.setGeometry(QtCore.QRect(1215, 620, 100, 16))
		self.label_7.setObjectName("label_7")
		
		self.w_parameter_list = QtWidgets.QListView(self.centralwidget)
		self.w_parameter_list.setGeometry(QtCore.QRect(660, 265, 405, 220))
		self.w_parameter_list.setObjectName("w_parameter_list")
		self.w_parameter_label = QtWidgets.QLabel(self.centralwidget)
		self.w_parameter_label.setGeometry(QtCore.QRect(670, 270, 220, 16))
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
		self.w_enter_button.setGeometry(QtCore.QRect(670, 450, 90, 30))
		self.w_enter_button.setObjectName("w_enter_button")
		
		self.w_cal_button = QtWidgets.QPushButton(self.centralwidget)
		self.w_cal_button.setGeometry(QtCore.QRect(930, 310, 90, 30))
		self.w_cal_button.setObjectName("w_cal_button")
		self.w_cal_button_label = QtWidgets.QLabel(self.centralwidget)
		self.w_cal_button_label.setGeometry(QtCore.QRect(920, 340, 131, 40))
		self.w_cal_button_label.setObjectName("w_cal_button_label")
		self.w_cal_button_label_2 = QtWidgets.QLabel(self.centralwidget)
		self.w_cal_button_label_2.setGeometry(QtCore.QRect(910, 270, 150, 40))
		self.w_cal_button_label_2.setObjectName("w_cal_button_label_2")
		
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
		self.auto_roi = QtWidgets.QPushButton(self.centralwidget)
		self.auto_roi.setGeometry(QtCore.QRect(210, 220, 75, 23))
		self.auto_roi.setObjectName("auto_roi")
		self.manual_roi = QtWidgets.QPushButton(self.centralwidget)
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
		self.save_list.setGeometry(QtCore.QRect(1090, 265, 120, 160))
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
		self.save_file_edit.setGeometry(QtCore.QRect(1100, 350, 104, 31))
		self.save_file_edit.setObjectName("save_file_edit")
		self.save_function_button = QtWidgets.QPushButton(self.centralwidget)
		self.save_function_button.setGeometry(QtCore.QRect(1100, 390, 75, 25))
		self.save_function_button.setObjectName("save_function_button")
		
		self.statusbar.showMessage("INITIALING")
		self.retranslateUi(mainwindow)
		QtCore.QMetaObject.connectSlotsByName(mainwindow)
		
		self.start.clicked.connect(self.start_clicked)
		self.x_axis.clicked.connect(self.x_axis_clicked)	
		self.y_axis.clicked.connect(self.y_axis_clicked)
		self.w_x_axis.clicked.connect(self.w_x_axis_clicked)	
		self.w_y_axis.clicked.connect(self.w_y_axis_clicked)	
		self.auto_scaling.clicked.connect(self.auto_scaling_clicked)	
		self.auto_roi.clicked.connect(self.auto_roi_clicked)	
		self.manual_roi.clicked.connect(self.manual_roi_clicked)	
		self.w_cal_button.clicked.connect(self.w_cal_button_clicked)	
		self.cahnge_btn.clicked.connect(self.change_btn_clicked)	
		self.w_enter_button.clicked.connect(self.w_enter_button_clicked)	
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
		self.y_axis.setText(_translate("mainwindow", "AUTO"))
		self.x_axis_label.setText(_translate("mainwindow", "X Axis"))
		self.x_axis.setText(_translate("mainwindow", "AUTO"))
		self.w_x_axis_label.setText(_translate("mainwindow", "X Axis"))
		self.w_x_axis.setText(_translate("mainwindow", "AUTO"))
		self.w_y_axis.setText(_translate("mainwindow", "AUTO"))
		self.label_7.setText(_translate("mainwindow", "Y Axis"))
		self.a3_label.setText(_translate("mainwindow", "a3"))
		self.a2_label.setText(_translate("mainwindow", "a2"))
		self.a1_label.setText(_translate("mainwindow", "a1"))
		self.a0_label.setText(_translate("mainwindow", "a0"))
		self.e3_label.setText(_translate("mainwindow", "E"))
		self.e2_label.setText(_translate("mainwindow", "E"))
		self.e1_label.setText(_translate("mainwindow", "E"))
		self.e0_label.setText(_translate("mainwindow", "E"))
		self.w_enter_button.setText(_translate("mainwindow", "ENTER"))
		self.w_cal_button.setText(_translate("mainwindow", "Calculate"))
		self.w_cal_button_label.setText(_translate("mainwindow", "Press start to use\ncalculate"))
		self.max_shutter_label.setText(_translate("mainwindow", "Max: "+str(st_max)+"\u03BCs"))
		self.max_anologgain_label.setText(_translate("mainwindow", "Max: "+str(ag_max)))
		self.max_digitalgain_label.setText(_translate("mainwindow", "Not Functioning"))
		self.auto_roi_label.setText(_translate("mainwindow", "ROI Scan"))
		self.auto_roi.setText(_translate("mainwindow", "Auto"))
		self.manual_roi.setText(_translate("mainwindow", "Manual"))
		self.auto_scaling_label.setText(_translate("mainwindow", "Auto Scaling"))
		self.auto_scaling.setText(_translate("mainwindow", "START"))
		self.I_max_label.setText(_translate("mainwindow", "Intensity Max"))
		self.I_thr_percentage_label.setText(_translate("mainwindow", "Thersold (%)"))
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
		self.w_cal_button_label_2.setText(_translate("mainwindow", "Calculate Wavelength\nParameter"))
		self.w_parameter_label.setText(_translate("mainwindow", "Wavelength Calculation Parameters"))
		self.save_label.setText(_translate("mainwindow", "Save Function"))
		self.save_rd_data_checkbox.setText(_translate("mainwindow", "Raw Data"))
		self.save_sg_data_checkbox.setText(_translate("mainwindow", "SG Data"))
		self.save_file_label.setText(_translate("mainwindow", "Save File Name"))
		self.save_function_button.setText(_translate("mainwindow", "Save"))

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
		
		self.manual_roi.setEnabled(False)
		self.Xaxis_min.setEnabled(False)
		self.Xaxis_max.setEnabled(False)
		self.Yaxis_min.setEnabled(False)
		self.Yaxis_max.setEnabled(False)
		self.W_Xaxis_min.setEnabled(False)
		self.W_Xaxis_max.setEnabled(False)
		self.W_Yaxis_min.setEnabled(False)
		self.W_Yaxis_max.setEnabled(False)
		self.w_cal_button.setEnabled(False)
		self.save_file_edit.setEnabled(False)
		self.save_function_button.setEnabled(False)
		
	def start_clicked(self):
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
			
		self.w_cal_button.setEnabled(True)
		self.w_cal_button_label.setVisible(False)
		thread1 = threading.Thread(target = thread_1)
		thread1.daemon = True
		thread1.start()
		
	def y_axis_clicked(self):
		global y_mode
		_translate = QtCore.QCoreApplication.translate
		
		if y_mode == 0: 
			yaxis_min = self.Yaxis_min.text()
			yaxis_max = self.Yaxis_max.text()
			
			self.pixel_graph.setYRange(int(yaxis_min), int(yaxis_max), padding=0)
			self.y_axis.setText(_translate("mainwindow", "FIX"))
			self.Yaxis_min.setEnabled(True)
			self.Yaxis_max.setEnabled(True)
			y_mode = 1
		elif y_mode == 1:
			self.pixel_graph.enableAutoRange(axis='y')
			self.y_axis.setText(_translate("mainwindow", "AUTO"))
			self.Yaxis_min.setEnabled(False)
			self.Yaxis_max.setEnabled(False)
			y_mode = 0
			
	def x_axis_clicked(self):
		global x_mode
		_translate = QtCore.QCoreApplication.translate
		
		if x_mode == 0: 
			xaxis_min = self.Xaxis_min.text()
			xaxis_max = self.Xaxis_max.text()
			self.pixel_graph.setXRange(int(xaxis_min), int(xaxis_max), padding=0)
			self.x_axis.setText(_translate("mainwindow", "FIX"))
			self.Xaxis_min.setEnabled(True)
			self.Xaxis_max.setEnabled(True)
			x_mode = 1
		elif x_mode == 1:
			self.pixel_graph.enableAutoRange(axis='x')
			self.x_axis.setText(_translate("mainwindow", "AUTO"))
			self.Xaxis_min.setEnabled(False)
			self.Xaxis_max.setEnabled(False)
			x_mode = 0
	   
	def w_y_axis_clicked(self):
		global w_y_mode
		_translate = QtCore.QCoreApplication.translate
		
		if w_y_mode == 0: 
			yaxis_min = self.W_Yaxis_min.text()
			yaxis_max = self.W_Yaxis_max.text()
			
			self.wavelength_graph.setYRange(int(yaxis_min), int(yaxis_max), padding=0)
			self.w_y_axis.setText(_translate("mainwindow", "FIX"))
			self.W_Yaxis_min.setEnabled(True)
			self.W_Yaxis_max.setEnabled(True)
			w_y_mode = 1
		elif w_y_mode == 1:
			self.wavelength_graph.enableAutoRange(axis='y')
			self.w_y_axis.setText(_translate("mainwindow", "AUTO"))
			self.W_Yaxis_min.setEnabled(False)
			self.W_Yaxis_max.setEnabled(False)
			w_y_mode = 0
			
	def w_x_axis_clicked(self):
		global w_x_mode
		_translate = QtCore.QCoreApplication.translate
		
		if w_x_mode == 0: 
			xaxis_min = self.W_Xaxis_min.text()
			xaxis_max = self.W_Xaxis_max.text()
			self.wavelength_graph.setXRange(int(xaxis_min), int(xaxis_max), padding=0)
			self.w_x_axis.setText(_translate("mainwindow", "FIX"))
			self.W_Xaxis_min.setEnabled(True)
			self.W_Xaxis_max.setEnabled(True)
			w_x_mode = 1
		elif w_x_mode == 1:
			self.wavelength_graph.enableAutoRange(axis='x')
			self.w_x_axis.setText(_translate("mainwindow", "AUTO"))
			self.W_Xaxis_min.setEnabled(False)
			self.W_Xaxis_max.setEnabled(False)
			w_x_mode = 0
			
	def auto_scaling_clicked(self):
		global auto_mode
		
		auto_mode = 10
		
		thread2 = threading.Thread(target = thread_2)
		thread2.daemon = True
		thread2.start()
	
	def auto_roi_clicked(self):
		global roi_mode, mode, flag
		_translate = QtCore.QCoreApplication.translate
		roi_mode=0
		mode = 10
		self.x0.setEnabled(False)
		self.y0.setEnabled(False)
		self.x1.setEnabled(False)
		self.auto_roi.setEnabled(False)
		thread1 = threading.Thread(target = thread_1)
		thread1.daemon = True
		thread1.start()
		
	def manual_roi_clicked(self):
		global roi_mode, mode, flag
		_translate = QtCore.QCoreApplication.translate
		roi_mode=1
		self.x0.setEnabled(True)
		self.y0.setEnabled(True)
		self.x1.setEnabled(True)
		self.manual_roi.setEnabled(False)
		self.auto_roi.setEnabled(True)
		
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
	
	def w_enter_button_clicked(self):
		check = wavelength_convert()
		if check!=1:
			raise Exception
		check = self.draw_wavelength_graph_signal()
		if check!=1:
			raise Exception
			
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
	
	def save_function_button_clicked(self):
		try:
			self.statusbar.showMessage("Saving")
			if self.save_rd_data_checkbox.isChecked():
				path = self.save_file_edit.text() + "_raw.txt"
				s = ncolmean
				check = self.helper_save_funtion(path, s)
				if check != 1:
					raise Exception
					
			if self.save_sg_data_checkbox.isChecked():
				path = self.save_file_edit.text() + "_sg.txt"
				s = signal.savgol_filter(ncolmean, int(self.window_length_edit.text()), int(self.polyorder_edit.text()))
				check = self.helper_save_funtion(path, s)
				if check != 1:
					raise Exception
					
			print("Save Complete")
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
			self.save_function_button.setEnabled(True)
		elif self.save_rd_data_checkbox.isChecked() == False and self.save_sg_data_checkbox.isChecked() == False :
			self.save_file_edit.setEnabled(False)
			self.save_function_button.setEnabled(False)
			
	def y_axis_fix(self):
		yaxis_min = self.Yaxis_min.text()
		yaxis_max = self.Yaxis_max.text()
		self.pixel_graph.setYRange(int(yaxis_min), int(yaxis_max), padding=0)
		
	def x_axis_fix(self):
		xaxis_min = self.Xaxis_min.text()
		xaxis_max = self.Xaxis_max.text()
		self.pixel_graph.setXRange(int(xaxis_min), int(xaxis_max), padding=0)
		
	def w_y_axis_fix(self):
		yaxis_min = self.W_Yaxis_min.text()
		yaxis_max = self.W_Yaxis_max.text()
		self.wavelength_graph.setYRange(int(yaxis_min), int(yaxis_max), padding=0)
		
	def w_x_axis_fix(self):
		xaxis_min = self.W_Xaxis_min.text()
		xaxis_max = self.W_Xaxis_max.text()
		self.wavelength_graph.setXRange(int(xaxis_min), int(xaxis_max), padding=0)
	
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
		check = ui.draw_spectrum_graph_signal()
		if check != 1:
			raise Exception
		check = ui.update_image_signal()
		if check != 1:
			raise Exception
		check = wavelength_convert()
		if check != 1:
			raise Exception
		check = ui.draw_wavelength_graph_signal()
		if check != 1:
			raise Exception
		print("ROI DONE")
	
	def auto_scaling_paremeter_change(self):
		_translate = QtCore.QCoreApplication.translate
		
		I_max = int(ui.I_max_edit.text())
		I_thr_percentage = int(ui.I_thr_percentage_edit.text())
		I_thr_tolerance = int(ui.I_thr_tolerance_edit.text())
		I_thr = I_max * I_thr_percentage/100
		I_thr_top = I_thr + I_thr_tolerance
		I_thr_bottom = I_thr - I_thr_tolerance
		self.I_thr_tolerance_label1.setText(_translate("mainwindow", str(I_thr_top) + '~' + str(I_thr_bottom)))
		self.I_thr_percentage_label1.setText(_translate("mainwindow", str(I_thr)))
		
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
			
			return 1
		except Exception as e:
			print('error:{}'.format(e))
			return 0
			
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
		
	def update_data(self):
		try:
			self.pixel_graph.clear()
			x = np.arange(1,len(ncolmean)+1)
			if self.sg_filter_checkbox.isChecked():
				#savgol_filter(data, window length, polyorder)
				y = signal.savgol_filter(ncolmean, int(self.window_length_edit.text()), int(self.polyorder_edit.text()))
			else:
				y = ncolmean
			self.pixel_graph.plot(x, y, pen=pg.mkPen('k'))	# k = black
			
			return 1
		except Exception as e:
			print('error:{}'.format(e))
			return 0	
	
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
	
	def update_st(self):
		try:
			self.shutter_edit.setText(str(goal_st))
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
							
def takephoto():
	try:
		shutter = ui.shutter_edit.text()
		anolog_gain = ui.anologgain_edit.text()
		digital_gain = ui.digitalgain_edit.text()
		imgformat = ui.format_box.currentText().lower()
		
		imgname = "./ttest/test.{}".format(imgformat)
		subprocess.run(["libcamera-still", "--shutter", shutter, "--analoggain", anolog_gain, "-o", imgname,"--immediate","--nopreview"])
		return 1
	except Exception as e:
		print('error:{}'.format(e))
		return 0	
		
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
		
def checkluminous():
	try:
		sh = int(ui.shutter_edit.text())
		if(sh>=1000000):
			raise Exception
		if (max_value >= I_max):
			return '0'
		elif (max_value > I_thr_top):
			return '1'
		elif (max_value < I_thr_top and max_value > I_thr_bottom):
			return '2'
		elif (max_value < I_thr_bottom):
			return '3'
	except Exception as e:
		print('error:{}'.format(e))
		return 0
		
def set_half_exp():
	global st1, I1
	
	try:
		st1 = float(ui.shutter_edit.text())
		I1 = max_value
		
		st = int(ui.shutter_edit.text())
		ui.shutter_edit.setText(str(int(st/2)))
		return 1
	except Exception as e:
		print('error:{}'.format(e))
		return 0

def set_double_exp():
	global st1, I1
	
	try:
		st1 = float(ui.shutter_edit.text())
		I1 = max_value
		
		st = int(ui.shutter_edit.text())
		ui.shutter_edit.setText(str(int(st*2)))
		return 1
	except Exception as e:
		print('error:{}'.format(e))
		return 0

def find_target_exp():
	global goal_st
	
	try:
		st2 = float(ui.shutter_edit.text())
		I2 = max_value
		
		goal_st = int(st1 + ((st1 - st2)/(I1 - I2) * (I_thr - I1)))
		if goal_st > st_max:
			print("Can't calculate shutter")
			goal_st = shutter
		elif goal_st < 0:
			print("Goal Error")
			goal_st = shutter
			
		signalComm.new_goal_st.emit()
		return 1
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
	global ncolmean
	try:
		ncolmean = np.mean(np.asarray(numb_ofscan), axis = 0)

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
	
def thread_1(): #main function
	global mode, image_mode, numb_ofscan, roi_mode
	scan_time = 0
	first_scan = 1
	
	ui.statusbar.showMessage("CAPTURING IMAGE")
	
	while True:
		if mode == 0:
			if flag == 1:
				mode = 10
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
	if(roi_mode == 0):
		_translate = QtCore.QCoreApplication.translate
		roi_mode = 1
		ui.manual_roi.setEnabled(True)
		ui.auto_roi.setEnabled(False)
		
	print("Main Function Complete")
	ui.statusbar.showMessage("CAPTURE IMAGE COMPLETE")
	
def thread_2(): #auto scaling
	global auto_mode
	t_times = 0
	first_scan = 1
	
	ui.statusbar.showMessage("AUTO SCALING")
	
	while True:
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
			if check == '0': # peak(max_value) > I_max
				auto_mode = 51
			elif check == '1': # peak(max_value) > I_thr_top
				auto_mode = 50
			elif check == '2': # peak(max_value) is acceptable 
				auto_mode = 70
			elif check == '3': # peak(max_value) < I_thr_buttom
				auto_mode = 55
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
		elif auto_mode == 60:
			check = find_target_exp()
			if check == 1:
				auto_mode = 10
				t_times = 0
			else:
				auto_mode = 999
		elif auto_mode == 70:
			check = numb_ofscan()
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
			check = ui.draw_spectrum_graph_signal()
			if check == 1:
				auto_mode = 110
			else:
				auto_mode = 999
		elif auto_mode == 110:
			check = ui.update_image_signal()
			if check == 1:
				break
			else:
				auto_mode = 999
		elif auto_mode == 999:
			print("Auto Scaling Error")
			ui.statusbar.showMessage("AUTO SCALING Error")
			raise Exception
	print('Auto Scaling Complete')
	ui.statusbar.showMessage("AUTO SCALING Complete")

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
		 
if __name__ == "__main__":
	try:		
		app = QtWidgets.QApplication(sys.argv)
		mainwindow = QtWidgets.QMainWindow()
		secondwindow = QtWidgets.QMainWindow()
		signalComm = SignalCommunication()	
		ui = Ui_mainwindow()
		c_ui = Ui_w_calibration()
		ui.setupUi(mainwindow)
		c_ui.setupUi(secondwindow)
		mainwindow.show()
		sys.exit(app.exec_())
	except Exception as ex:
		print(ex)
		exit()
