'''
Contains Focus Tracking Wizard Class: autogenerates start end end foci from reference / anchor positions

'''

from PyQt5 import QtWidgets, QtGui, QtCore

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtProperty

from ..mesoSPIM_State import mesoSPIM_StateSingleton

class FocusTrackingWizard(QtWidgets.QWizard):
    '''
    Wizard to run

    The parent is the Window class of the microscope
    '''
    wizard_done = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        ''' By an instance variable, callbacks to window signals can be handed
        through '''
        self.parent = parent
        self.state = mesoSPIM_StateSingleton()

        self.f_1 = 0
        self.f_2 = 0
        self.z_1 = 0
        self.z_2 = 0
        
        self.setWindowTitle('Foucs Tracking Wizard')

        self.addPage(FocusTrackingWizardWelcomePage(self))
        self.addPage(FocusTrackingWizardSetReferencePointsPage(self))
        self.addPage(FocusTrackingWizardCheckResultsPage(self))
        
        self.show()

    def done(self, r):
        ''' Reimplementation of the done function

        if r == 0: canceled
        if r == 1: finished properly
        '''
        if r == 0:
            print("Wizard was canceled")
        if r == 1:
            print('Wizard was closed properly')
            # print('Laser selected: ', self.field('Laser'))
            self.update_focus_positions_in_model()
        else:
            print('Wizard provided return code: ', r)

        super().done(r)

    def calculate_f_pos(self, z_1, z_2, f_1, f_2, z):
        return (f_2-f_1)/(z_2-z_1)*(z-z_1)+f_1
    
    def update_focus_positions_in_model(self):
        row_count = self.parent.model.rowCount()
        z_start_column =  self.parent.model.getColumnByName('Z_start')
        z_end_column = self.parent.model.getColumnByName('Z_end')
        f_start_column = self.parent.model.getColumnByName('F_start')
        f_end_column = self.parent.model.getColumnByName('F_end')

        for row in range(0, row_count):
            z_start = self.parent.model.getZStartPosition(row)
            z_end = self.parent.model.getZEndPosition(row)

            f_start = self.calculate_f_pos(self.z_1, self.z_2, self.f_1, self.f_2, z_start)
            f_end = self.calculate_f_pos(self.z_1, self.z_2, self.f_1, self.f_2, z_end)

            f_start_index = self.parent.model.createIndex(row, f_start_column)
            f_end_index = self.parent.model.createIndex(row, f_end_column)

            self.parent.model.setData(f_start_index, f_start)
            self.parent.model.setData(f_end_index, f_end)

            

class FocusTrackingWizardWelcomePage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.setTitle("Welcome to the focus tracking wizard!")
        self.setSubTitle("This wizard allows you to set the correct focus start and end points by focusing manually at two reference points inside the sample. ATTENTION: All focus values will be overwritten!")
    
class FocusTrackingWizardSetReferencePointsPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.setTitle("Reference point definition")
        self.setSubTitle("Between z_start and z_end, focus the microscope at two different z-positions inside the sample.")

        self.button0 = QtWidgets.QPushButton(self)
        self.button0.setText('Set first reference point')
        self.button0.setCheckable(True)
        self.button0.toggled.connect(self.get_first_reference_point)

        self.button1 = QtWidgets.QPushButton(self)
        self.button1.setText('Set second reference point')
        self.button1.setCheckable(True)
        self.button1.toggled.connect(self.get_second_reference_point)

        self.registerField('set_first_refpoint*',
                            self.button0,
                            )
        self.registerField('set_second_refpoint*',
                            self.button1,
                            )

        self.layout = QtWidgets.QGridLayout()
        self.layout.addWidget(self.button0, 0, 0)
        self.layout.addWidget(self.button1, 0, 1)
        self.setLayout(self.layout)

    def get_first_reference_point(self):
        self.parent.f_1 = self.parent.state['position']['f_pos']
        self.parent.z_1 = self.parent.state['position']['z_pos']
        
    def get_second_reference_point(self):
        self.parent.f_2 = self.parent.state['position']['f_pos']
        self.parent.z_2 = self.parent.state['position']['z_pos']

    def validatePage(self):
        '''Further validation operations can be introduced here'''
        return super().validatePage()

class FocusTrackingWizardCheckResultsPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.setTitle('Finished!')
        '''
        self.setSubTitle('Please check if the following filenames are ok:')

        self.TextEdit = QtWidgets.QPlainTextEdit(self)
        self.TextEdit.setReadOnly(True)

        self.mystring = ''        
        self.TextEdit.setPlainText(self.mystring)

        self.layout = QtWidgets.QGridLayout()
        self.layout.addWidget(self.TextEdit, 0, 0, 1, 1)
        self.setLayout(self.layout)
        '''
    