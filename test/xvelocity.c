#include "udf.h"

/*  profile for x-velocity    */


DEFINE_PROFILE(x_velocity,t,i)
{
  real y, del, h, x[ND_ND], ufree;      /* variable declarations */
  face_t f;

  h = YMAX - YMIN;
  del = DELOVRH*h;
  ufree = UMEAN*(B+1.);

  begin_f_loop(f,t)
    {
      F_CENTROID(x,f,t);
      y = x[1];

      if (y <= del)
         F_PROFILE(f,t,i) = ufree*pow(y/del,B);
      else
         F_PROFILE(f,t,i) = ufree*pow((h-y)/del,B);
    }
  end_f_loop(f,t)
}