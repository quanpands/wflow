/*!
\note
Do not edit, generated from libs/pcrxml/generate.py
*/
#ifndef INCLUDED_PCRGENXML_LODINGINPUTTYPE
#define INCLUDED_PCRGENXML_LODINGINPUTTYPE


#ifndef INCLUDED_PCRXML_ATTRIBUTE
#include "pcrxml_attribute.h"
#define INCLUDED_PCRXML_ATTRIBUTE
#endif




class QDomElement;

namespace pcrxml{
class LodingInputType : public Attribute {
  public:
   typedef enum EnumType {
     ASCII=0,RWSLOD=1
   } EnumType;
  private:
   EnumType d_value;
  public:
   LodingInputType();
   LodingInputType(EnumType value);
   LodingInputType(
    const QDomNode& owningElement, const std::string& nameOfAttr, bool req);

   //! return value
   EnumType  operator()() const
        { return value(); };


   //! return value
   EnumType  value()      const
        { PRECOND(present());return d_value; };

   //! return enum value as string, (?? empty if not present ??)
   std::string attrValueStr() const;

   //! is value present and set to \a value ?
   bool operator==(EnumType value) const {
        return present()&& d_value==value;
   };

   //! is value not present or not equal to \a value ?
   /*! use is confusing, !(LodingInputType == EnumType) better?
    */
   bool operator!=(EnumType value) const {
        return !present() || d_value!=value;
   };

   void set(EnumType value) {
     d_value=value;
     setPresent(true);
   }
   void operator=(EnumType value) {
     set(value);
   }

  };
}


#endif
