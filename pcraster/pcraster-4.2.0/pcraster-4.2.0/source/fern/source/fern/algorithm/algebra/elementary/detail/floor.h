// -----------------------------------------------------------------------------
// Fern © Geoneric
//
// This file is part of Geoneric Fern which is available under the terms of
// the GNU General Public License (GPL), version 2. If you do not want to
// be bound by the terms of the GPL, you may purchase a proprietary license
// from Geoneric (http://www.geoneric.eu/contact).
// -----------------------------------------------------------------------------
#pragma once
#include <cmath>
#include "fern/core/assert.h"
#include "fern/algorithm/policy/policies.h"
#include "fern/algorithm/core/unary_local_operation.h"


namespace fern {
namespace algorithm {
namespace floor {
namespace detail {

template<
    typename Value>
struct Algorithm
{

    FERN_STATIC_ASSERT(std::is_floating_point, Value)

    template<
        typename Result>
    inline void operator()(
        Value const& value,
        Result& result) const
    {
        FERN_STATIC_ASSERT(std::is_same, Result, Value)

        result = std::floor(value);
    }

};


template<
    typename InputNoDataPolicy,
    typename OutputNoDataPolicy,
    typename ExecutionPolicy,
    typename Value,
    typename Result
>
void floor(
    InputNoDataPolicy const& input_no_data_policy,
    OutputNoDataPolicy& output_no_data_policy,
    ExecutionPolicy& execution_policy,
    Value const& value,
    Result& result)
{
    unary_local_operation<Algorithm,
        unary::DiscardDomainErrors, unary::DiscardRangeErrors>(
            input_no_data_policy, output_no_data_policy,
            execution_policy,
            value, result);
}

} // namespace detail
} // namespace floor
} // namespace algorithm
} // namespace fern
