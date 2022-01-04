from fluentpy.tui import WallBoundaryCondition,UDF,MassFlowInlet,PressureOutlet,Solver,Solver_Iterator,\
                                FluentJournal,ConvergenceConditions,Discritization,NISTRealGas,ScalarRelaxation,\
                                EquationRelaxation, VelocityInlet
from fluentpy.util import _surface_construction_arg_validator

from unittest import TestCase,main
import shutil

"""
-- Creation -- 
Date: 11.28.2021
Author: Michael Lanahan

-- Last Edit -- 
Date: 12.28.2021
Editor: Michael Lanahan

-- Further Description --

Checking the function of the io classes


Remaining Basic Unit Tests to Write
-----------------------------------

- Initializer
- CaseReader
- CaseMeshReplaceReader
- CaseDataReader
- FluentEngine
- BatchCaseReader
- DataWriter
- CaseWriter
- Solver_Iterator
- Solver
- FluentCase
- StandardKOmegaSpecification
- StandardKEpsilonSpecification
- ViscousModelModification
- SolidCellZone
- WallBoundaryCondition
- SurfaceIntegrals
"""

"""
class TestUDF(TestCase):

    check_wall_udf  = 'test-files\\check\\check_wall_udf.txt'

    def test_wall_udf(self):
        wall = WallBoundaryCondition('test',['energy','viscous'],'pressure-based')
        wall.free_stream_temperature = 400.0
        udf = UDF('test.c','udf','HTC::UDF','convection_coefficient')
        wall.add_udf(udf)
        text = wall()
        
        with open(self.check_wall_udf,'r') as file:
            check = file.read()
        
        self.assertEqual(text,check)

class TestMassFlowInlet(TestCase):

    check_mfi = 'test-files\\check\\check_mass_flow_inlet.txt'

    def get_test_mfr(self):

        mass_flow = MassFlowInlet('inner_tube_inlet',['energy','ke-standard'],'pressure-based','ke-standard')
        mass_flow.mass_flow_rate = 0.04
        mass_flow.init_pressure = 4.2e6
        mass_flow.temperature = 360
        mass_flow.turbulence_model.hydraulic_diameter = 0.013
        mass_flow.turbulence_model.intensity = 3.8
        return mass_flow

    def test_mass_flow_rate(self):

        mfi = self.get_test_mfr()
        text = mfi()
        
        with open(self.check_mfi,'r') as file:
            check = file.read()

        self.assertEqual(text,check)

class TestPressureOutlet(TestCase):

    check_po = 'test-files\\check\\check_pressure_outlet.txt'

    def get_test_pressure(self):
        pressure_outlet = PressureOutlet('outer_tube_outlet',['energy','viscous'],'pressure-based','kw-standard')
        pressure_outlet.pressure = 4.3e6
        pressure_outlet.temperature = 320
        pressure_outlet.turbulence_model.hydraulic_diameter = 0.003
        pressure_outlet.turbulence_model.intensity = 3.8

        return pressure_outlet

    def test_pressure_outlet(self):

        po = self.get_test_pressure()
        text  = po()
        
        with open(self.check_po,'r') as file:
            check = file.read()
        
        self.assertEqual(text,check)

class TestFluentRun(TestCase):

    input_file = 'test-files\\test\\fluent_run_input.input'
    input_check = 'test-files\\check\\check_fluentrun_input.txt'

    def test_fluent_run(self):

        mfr = TestMassFlowInlet().get_test_mfr()
        po = TestPressureOutlet().get_test_pressure()
        solver = Solver(solver_iterator= Solver_Iterator(niter = 500))
        ff = FluentRun('test.cas',solver = solver, boundary_conditions= [mfr,po])
        ff.write(self.input_file)
        shutil.copy2(self.input_file,self.input_check)

        with open(self.input_check,'r') as file:
            check = file.read()
        
        with open(self.input_file,'r') as file:
            test = file.read()

        self.assertEqual(check,test)
    
class TestConvergenceConditions(TestCase):

    cc_check = 'test-files\\check\\check_convergence_conditions.txt'

    def test_convergence_conditions(self):
        cc = ConvergenceConditions(['p-out','max-temp'])
        text = str(cc)
        with open(self.cc_check,'r') as file:
            check = file.read()
        
        self.assertEqual(text,check)

class TestDiscritization(TestCase):

    disc_check1 = 'test-files\\check\\check_discritization1.txt'
    disc_check2 = 'test-files\\check\\check_discritization2.txt'
    disc_check3 = 'test-files\\check\\check_discritization3.txt'

    def test_disciritization_conditions(self):
        
        for file_name,order in zip([self.disc_check1,self.disc_check2,self.disc_check3],\
                             ['First Order Upwind','Second Order Upwind','Third Order MUSCL']):
                
            disc = Discritization(orders = order)
            
            with open(file_name,'r') as file:
                check = file.read()
            
            self.assertEqual(str(disc),check)

class TestNistRealGas(TestCase):

    nist_rg_check1 = 'test-files\\check\\nist-real-gas-co2.txt'

    def test_nrg(self):

        nrg = NISTRealGas('co2')
        
        with open(self.nist_rg_check1,'r') as file:
            check = file.read()
        
        self.assertEqual(str(nrg),check)

class TestScalarRelaxation(TestCase):

    sr_file = 'test-files\\check\\scalar_relaxation.txt'

    def test_sr(self):
        relaxation = ScalarRelaxation(['density','temperature'],[0.8,0.7])
        
        with open(self.sr_file,'r') as file:
            check = file.read()
        
        self.assertEqual(str(relaxation),check)

class TestEquationRelaxation(TestCase):

    er_file1 = 'test-files\\check\\equation_relaxation1.txt'
    er_file2 = 'test-files\\check\\equation_relaxation2.txt'

    def test_er(self):
        relaxation = EquationRelaxation('pressure',0.8)

        with open(self.er_file1,'r') as file:
            check = file.read()
        
        self.assertEqual(str(relaxation),check)

    def test_er_list(self):
        relaxation = EquationRelaxation(['pressure','momentum'],[0.8,0.7])
        
        with open(self.er_file2,'r') as file:
            check = file.read()
        
        self.assertEqual(str(relaxation),check)

class TestSurfaceIntegrals(TestCase):

    def test_scav_single(self):

        output = _surface_construction_arg_validator(11,'temperature','area-weighted-avg')
        self.assertListEqual(output[0],['11'])
        self.assertListEqual(output[1],['temperature'])
        self.assertListEqual(output[2],['area-weighted-avg'])
    
    def test_scav_multiple_id(self):

        output = _surface_construction_arg_validator([[10,11],12],
                                                     ['temperature','temperature'],
                                                     ['area-weighted-avg','area-weighted-avg'])
        
        self.assertListEqual(output[0],[['12'],['10','11']])
        self.assertListEqual(output[1],['temperature','temperature'])
        self.assertListEqual(output[2],['area-weighted-avg','area-weighted-avg'])
"""

class TestVelocityInlet(TestCase):

    def test_normal_initalization(self):

        vi = VelocityInlet('velocity_inlet',['viscous'],'pressure-based','ke-standard',
                            precision_specification = '2ddp')
        print(vi())
    

if __name__ == '__main__':
    main()