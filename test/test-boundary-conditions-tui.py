from unittest import TestCase,main
from fluentpy.tui import StandardKEpsilonSpecification, MassFlowInlet,PressureOutlet,\
                         WallBoundaryCondition, VelocityInlet

class TestStandardKEpsilonSpecification(TestCase):

    def test_k_eps_spec(self):

        keps = StandardKEpsilonSpecification(turbulent_dissipation_rate = 1.0,
                                             turbulent_kinetic_energy = 1.0)
        
        #print(keps.format_boundary_condition())
    
    def test_intensity_and_length_scale_spec(self):

        keps = StandardKEpsilonSpecification(turb_intensity = 5.0)
        keps.turb_length_scale = 10.0

        #print(keps.format_boundary_condition())

    def test_intensity_and_viscosity_ratio_spec(self):

        keps = StandardKEpsilonSpecification()
        keps.turb_intensity = 5.0
        keps.turb_viscosity_ratio = 99.9

        #print(keps.format_boundary_condition())

    def test_intensity_and_diameter(self):

        keps = StandardKEpsilonSpecification(turb_hydraulic_diam = 0.01)
        keps.turb_intensity = 55.0

        #print(keps.format_boundary_condition())

class TestMassFlowInlet(TestCase):

    def test_direction(self):

        mfi = MassFlowInlet('mass-flow-inlet',['viscous','energy'],'ke-standard')

        #print(mfi.format_direction_spec())

        mfi.direction_vector = [0.5,0.25,1.0]
        #print(mfi.format_direction_spec())

    def test_format_frame_of_reference(self):

        mfi = MassFlowInlet('mass-flow-inlet',['viscous','energy'],'ke-standard')

        #print(mfi.format_frame_of_reference())

        mfi.frame_of_reference = 'relative to adjacent cell zone'

        #print(mfi.format_frame_of_reference())
    
    def test_format_conditions(self):

        mfi = MassFlowInlet('mass-flow-inlet',['viscous','energy'],'ke-standard')
        mfi.turbulence_model.turb_intensity = 1.0
        mfi.turbulence_model.turb_length_scale = 5.0

        #print(mfi.format_conditions())

    def test_format_specifications(self):

        mfi = MassFlowInlet('mass-flow-inlet',['viscous','energy'],'ke-standard')
        mfi.mass_flux = 1.0
        mfi.turbulence_model.turb_intensity = 1.0
        mfi.turbulence_model.turb_length_scale = 5.0
        #print(mfi.format_boundary_condition())

class TestPressureOutlet(TestCase):


    def test_boolean_conditions(self):

        po = PressureOutlet('pressure-outlet',['viscous','energy'],'ke-standard',pressure = 1e5)

        po.radial = True
        #print(po.radial)

        #print(po.avg_press_spec)

    def test_format_conditions(self):

        po = PressureOutlet('pressure-outlet',['viscous','energy'],'ke-standard',pressure = 1e5)
        po.turbulence_model.turb_intensity = 1.0
        po.turbulence_model.turb_length_scale = 5.0
        #print(po.format_conditions())
    
    def test_format_boundary_condition(self):

        po = PressureOutlet('pressure-outlet',['viscous','energy'],'ke-standard',pressure = 1e5)
        po.turbulence_model.turbulent_kinetic_energy = 1.0
        po.turbulence_model.turbulent_dissipation_rate = 5.0
        #print(po.format_boundary_condition())

class TestWall(TestCase):

    def test_no_energy(self):

        wall = WallBoundaryCondition('heated-surf',['viscous'])
        #print(wall.format_boundary_condition())
    
    def test_convection(self):

        wall = WallBoundaryCondition('heated-surf',['viscous','energy'])
        wall.convective_heat_transfer_coefficient = 10
        wall.tinf = 500
        #print(wall.format_boundary_condition())

    def test_heat_flux(self):

        wall = WallBoundaryCondition('heated-surf',['viscous','energy'])
        wall.heat_flux = 10e3
        #print(wall.format_boundary_condition())
    
    def test_radiation(self):
        wall = WallBoundaryCondition('heated-surf',['viscous','energy'])
        wall.trad = 1e4
        wall.ex_emiss = 0.5

        #print(wall.format_boundary_condition())

    def test_mixed(self):

        wall = WallBoundaryCondition('heated-surf',['viscous','energy'])
        wall.heat_flux = 10e3
        wall.trad = 1e4
        wall.ex_emiss = 0.5
        wall.convective_heat_transfer_coefficient = 10
        wall.tinf = 500
        #print(wall.format_boundary_condition())

class TestVelocityInlet(TestCase):

    def test_normal(self):

        vi = VelocityInlet('velocity_inlet',['viscous'],'viscous',vmag = 1.0)
        #print(vi())

    def test_velocity_specification(self):

        vi = VelocityInlet('velocity_inlet',['viscous'],'viscous',vmag = 1.0)
        vi.direction_vector = [1,1]
        print(vi())



if __name__ == '__main__':
    main()