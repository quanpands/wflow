#include <stdio.h>
#include "csf.h"

/* a simple csf to stdout
 * program, with minimal 
 * checking
 */

void main(int argc, char *argv[] )
{

  REAL4 cellValue;
  MAP *map;                      
  size_t r,c;

  if (argc != 2)
  {
   fprintf(stderr,"%s: no file specified\n",argv[0]);
   exit(1);
  }

  map = Mopen(argv[1], M_READ);
  if (map == NULL)
       MperrorExit(argv[1],1);

  if (RuseAs(map, CR_REAL4))
       MperrorExit(argv[1],1);

  for(r=0; r < RgetNrRows(map); r++)
  {
   for(c=0; c < RgetNrCols(map); c++)
   {
    RgetCell(map,r,c,&cellValue); 
    printf("%g ",(double)cellValue);
   }
   printf("\n");
  }

  Mclose(map);

  exit(0);
}
