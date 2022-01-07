#include "udf.h"

#define YMIN 0.0                        /* constants  */
#define YMAX 0.4064
#define UMEAN 1.0
#define B 1./7.
#define DELOVRH 0.5
#define VISC 1.7894e-05
#define CMU 0.09
#define VKC 0.41


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
