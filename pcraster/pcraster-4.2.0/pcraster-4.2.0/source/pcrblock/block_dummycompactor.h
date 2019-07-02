#ifndef INCLUDED_BLOCK_DUMMYCOMPACTOR
#define INCLUDED_BLOCK_DUMMYCOMPACTOR



#ifndef INCLUDED_STDDEFX
#include "stddefx.h"
#define INCLUDED_STDDEFX
#endif

// Library headers.

// PCRaster library headers.
#ifndef INCLUDED_PCRTYPES
#include "pcrtypes.h"
#define INCLUDED_PCRTYPES
#endif

// Module headers.



namespace block {
  // DummyCompactor declarations.
}



namespace block {



//! short_description_HORRIBLE_LONG_STRING_TO_NOTICE_THAT_IT_SHOULD_BE_REPLACED
/*!
  A Mackey and Bridge compactor.
*/
class DummyCompactor
{

  friend class DummyCompactorTest;

private:

protected:

public:

  //----------------------------------------------------------------------------
  // CREATORS
  //----------------------------------------------------------------------------

                   DummyCompactor      ();

  /* virtual */    ~DummyCompactor     ();

  //----------------------------------------------------------------------------
  // MANIPULATORS
  //----------------------------------------------------------------------------

  REAL4            operator()          (REAL4 originalThickness,
                                        REAL4 depth);

  //----------------------------------------------------------------------------
  // ACCESSORS
  //----------------------------------------------------------------------------

};



//------------------------------------------------------------------------------
// INLINE FUNCTIONS
//------------------------------------------------------------------------------



//------------------------------------------------------------------------------
// FREE OPERATORS
//------------------------------------------------------------------------------



//------------------------------------------------------------------------------
// FREE FUNCTIONS
//------------------------------------------------------------------------------



} // namespace block

#endif
