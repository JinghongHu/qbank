// kitty::hybrid_exact_spectral_canonization with a step limit on the exact (Miller) stage. When the limit is not
// reached the result is identical to the unlimited function (same search, not interrupted); when it is reached the
// second value is false and the representative must not be used.
#pragma once
#include <kitty/spectral.hpp>
#include <utility>
#include <vector>

template<typename TT, typename Callback>
std::pair<TT, bool> hybrid_canon_limit( const TT& tt, unsigned step_limit, Callback&& fn )
{
  std::vector<kitty::detail::spectral_operation> transforms;
  auto append = [&]( const auto& t ) { std::copy( t.begin(), t.end(), std::back_inserter( transforms ) ); };
  kitty::detail::anf_spectrum<TT> anf( tt );
  const bool is_disjoint = anf.classify();
  anf.get_transformations( append );
  if ( is_disjoint )
  {
    fn( transforms );
    return { anf.truth_table(), true };
  }
  const auto [miller_repr, exact] = kitty::exact_spectral_canonization_limit( anf.truth_table(), step_limit, append );
  if ( !exact )
    return { tt, false };
  kitty::detail::anf_spectrum<TT> anf_post( miller_repr );
  anf_post.classify();
  anf_post.get_transformations( append );
  fn( transforms );
  return { anf_post.truth_table(), true };
}
