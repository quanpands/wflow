// -----------------------------------------------------------------------------
// Fern © Geoneric
//
// This file is part of Geoneric Fern which is available under the terms of
// the GNU General Public License (GPL), version 2. If you do not want to
// be bound by the terms of the GPL, you may purchase a proprietary license
// from Geoneric (http://www.geoneric.eu/contact).
// -----------------------------------------------------------------------------
#include "fern/language/operation/core/argument_type.h"


namespace fern {
namespace language {

std::ostream& operator<<(
    std::ostream& stream,
    ArgumentType const& argument_type)
{
    switch(argument_type) {
        case ArgumentType::AT_ATTRIBUTE: {
            stream << "AT_ATTRIBUTE";
            break;
        }
        case ArgumentType::AT_FEATURE: {
            stream << "AT_FEATURE";
            break;
        }
    }

    return stream;
}

} // namespace language
} // namespace fern
