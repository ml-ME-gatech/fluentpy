from unittest import TestCase,main
from fluentpy.batch.table_parse import _parse_udf_from_str
from fluentpy.tui import WallBoundaryCondition

class TestUDFStringParse(TestCase):

    def test_wall_convection(self):
        test_str = '<test-files/test/xvelocity.c#compile = True>'

        udf = _parse_udf_from_str(test_str)
        #print(udf.compile)

        wall = WallBoundaryCondition('thimble_tp',['energy','viscous'])
        wall.__setattr__('convective_heat_transfer_coefficient',udf)

        print(wall())

if __name__ == '__main__':
    main()