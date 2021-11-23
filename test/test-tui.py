from fluentpy.tui.fluent import WallBoundaryCondition,UDF,MassFlowInlet,PressureOutlet,Solver,Solver_Iterator
from fluentpy.tui.fluent import FluentRun,ConvergenceConditions,Discritization,NISTRealGas,ScalarRelaxation
from fluentpy.tui.fluent import EquationRelaxation

def test_wall_udf():

    wall = WallBoundaryCondition('test',['energy','viscous'],'pressure-based')
    wall.free_stream_temperature = 400.0
    udf = UDF('test.c','udf','HTC::UDF','convection_coefficient')
    wall.add_udf(udf)
    text = wall.format_boundary_condition()
    print(text)

def get_test_mfr():

    mass_flow = MassFlowInlet('inner_tube_inlet',['energy','ke-standard'],'pressure-based')
    mass_flow.mass_flow_rate = 0.04
    mass_flow.init_pressure = 4.2e6
    mass_flow.temperature = 360
    mass_flow.hydraulic_diameter = 0.013
    mass_flow.intensity = 3.8

    return mass_flow

def get_test_pressure():
    pressure_outlet = PressureOutlet('outer_tube_outlet',['energy','ke-standard'],'pressure-based')
    pressure_outlet.pressure = 4.3e6
    pressure_outlet.temperature = 320
    pressure_outlet.hydraulic_diameter = 0.003
    pressure_outlet.intensity = 3.8

    return pressure_outlet

def test_fluent_run():
    
    mfr = get_test_mfr()
    po = get_test_pressure()

    solver = Solver(solver_iterator= Solver_Iterator(niter = 500))
    ff = FluentRun('test.cas',solver = solver, boundary_conditions= [mfr,po])
    ff.write('fleunt_input.fluent')

def test_mass_flow_rate_bc():

    mass_flow = get_test_mfr()
    mass_flow.udf = UDF('RadialHTCW10mm.c')

    #txt = mass_flow(turbulent_specification = 'Intensity and Hydraulic Diameter')
    #print(txt)


def test_pressure_outlet_bc():

    po = get_test_pressure()
    print(po())

def test_format_convergence_conditions():

    cc = ConvergenceConditions(['p-out','max-temp'])
    print(str(cc))

def test_discritization():

    disc = Discritization(orders = 'First Order Upwind')
    print(disc)

def test_real_gas():

    nrg = NISTRealGas('co2')
    print(nrg)

def test_scalar_relaxation():

    relaxation = ScalarRelaxation(['density','temperature'],[0.8,0.7])
    print(relaxation)

def test_equation_relaxation():

    #relax = EquationRelaxation('pressure',0.8)
    #print(relax)
    relax = EquationRelaxation.from_dict({'pressure':0.7})
    print(relax)

def main():
    test_wall_udf()

if __name__ == '__main__':
    main()