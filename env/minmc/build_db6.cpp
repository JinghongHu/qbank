// Convert NIST's AND-optimal circuits for the 150,357 affine classes of 6-variable Boolean functions
// (usnistgov/Circuits data/circuits/n6_circ.txt) into mockturtle's future::xag_minmc_resynthesis database format,
// keyed by kitty's hybrid exact spectral canonical representative. Every entry is checked twice: the NIST circuit
// against its ANF, and the transformed XAG against the canonical truth table.
#include <cstdio>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <kitty/kitty.hpp>
#include <mockturtle/networks/xag.hpp>
#include <mockturtle/algorithms/simulation.hpp>
#include <mockturtle/algorithms/equivalence_classes.hpp>
#include <mockturtle/algorithms/cleanup.hpp>
#include <mockturtle/utils/index_list/index_list.hpp>
#include "hybrid_limit.hpp"

using namespace mockturtle;
using sig = xag_network::signal;

static std::vector<std::string> split( std::string const& s, char c )
{
  std::vector<std::string> out; std::string cur;
  for ( char ch : s ) { if ( ch == c ) { out.push_back( cur ); cur.clear(); } else cur += ch; }
  out.push_back( cur ); return out;
}

// linear form "x1+x4" / "0" / "1+x2" over pis
static sig lin( xag_network& x, std::vector<sig> const& pis, std::string s )
{
  s.erase( std::remove( s.begin(), s.end(), ' ' ), s.end() );
  sig acc = x.get_constant( false );
  if ( s == "0" || s.empty() ) return acc;
  for ( auto const& t : split( s, '+' ) )
  {
    if ( t == "1" ) acc = x.create_not( acc );
    else if ( t[0] == 'x' ) acc = x.create_xor( acc, pis[std::stoul( t.substr( 1 ) ) - 1] );
    else throw std::runtime_error( "bad linear term " + t );
  }
  return acc;
}

static kitty::dynamic_truth_table anf_tt( std::string s, uint32_t n )
{
  kitty::dynamic_truth_table f( n );
  s.erase( std::remove( s.begin(), s.end(), ' ' ), s.end() );
  if ( s == "0" || s.empty() ) return f;
  for ( auto const& mono : split( s, '+' ) )
  {
    kitty::dynamic_truth_table m( n );
    kitty::create_from_hex_string( m, std::string( 1u << ( n - 2 ), 'f' ) );
    if ( mono != "1" )
      for ( auto const& v : split( mono.substr( 1 ), 'x' ) )
      {
        kitty::dynamic_truth_table xv( n ); kitty::create_nth_var( xv, std::stoul( v ) - 1 ); m &= xv;
      }
    f ^= m;
  }
  return f;
}

int main( int argc, char** argv )
{
  std::ifstream in( argv[1] );
  std::ofstream out( argv[2] );
  // optional: argv[3] = canonization step limit (0 = unlimited), argv[4] = file for records that reached the limit
  const unsigned step_limit = argc > 3 ? std::stoul( argv[3] ) : 0u;
  std::ofstream lim( argc > 4 ? argv[4] : "/dev/null" );
  uint64_t limited = 0;
  const uint32_t n = 6;
  std::string line; std::vector<std::string> rec;
  uint64_t ok = 0, bad_anf = 0, bad_tr = 0, total = 0;
  auto flush = [&]() {
    if ( rec.size() < 4 ) { rec.clear(); return; }
    ++total;
    std::string anf = rec[0], topo = rec[1];
    uint64_t omask = std::stoull( rec[2] );
    // topology tokens "(Ai L : L)" / "(Ai L : 0 1)"
    std::vector<std::pair<std::vector<int>, std::vector<int>>> sides;
    size_t p = 0;
    while ( ( p = topo.find( '(', p ) ) != std::string::npos )
    {
      size_t q = topo.find( ')', p );
      auto body = topo.substr( p + 1, q - p - 1 );          // "A1 L : 0 1"
      auto colon = body.find( ':' );
      auto parse = []( std::string s ) { std::vector<int> v; std::istringstream is( s ); std::string t; while ( is >> t ) if ( t != "L" && t[0] != 'A' ) v.push_back( std::stoi( t ) ); return v; };
      sides.push_back( { parse( body.substr( 0, colon ) ), parse( body.substr( colon + 1 ) ) } );
      p = q + 1;
    }
    size_t k = sides.size();
    if ( rec.size() != 3 + 2 * k + 1 ) { ++bad_anf; rec.clear(); return; }
    xag_network x;
    std::vector<sig> pis; for ( uint32_t i = 0; i < n; ++i ) pis.push_back( x.create_pi() );
    std::vector<sig> ands;
    for ( size_t i = 0; i < k; ++i )
    {
      sig a = lin( x, pis, rec[3 + 2 * i] ), b = lin( x, pis, rec[4 + 2 * i] );
      for ( int j : sides[i].first ) a = x.create_xor( a, ands[j] );
      for ( int j : sides[i].second ) b = x.create_xor( b, ands[j] );
      ands.push_back( x.create_and( a, b ) );
    }
    sig o = lin( x, pis, rec[3 + 2 * k] );
    for ( size_t i = 0; i < k; ++i ) if ( ( omask >> i ) & 1 ) o = x.create_xor( o, ands[i] );
    x.create_po( o );
    auto tt = simulate<kitty::dynamic_truth_table>( x, default_simulator<kitty::dynamic_truth_table>( n ) )[0];
    if ( tt != anf_tt( anf, n ) ) { ++bad_anf; rec.clear(); return; }
    std::vector<kitty::detail::spectral_operation> ops;
    const auto [repr, exact] = hybrid_canon_limit( tt, step_limit, [&]( auto const& t ) { ops = t; } );
    if ( !exact )
    {
      ++limited;
      for ( auto const& l : rec ) lim << l << "\n";
      lim << "\n";
      rec.clear();
      return;
    }
    // build the representative from the NIST circuit through the recorded operations (try both orders, keep the verified one)
    bool done = false;
    for ( int order = 0; order < 2 && !done; ++order )
    {
      auto seq = ops; if ( order ) std::reverse( seq.begin(), seq.end() );
      xag_network y;
      std::vector<sig> ypis; for ( uint32_t i = 0; i < n; ++i ) ypis.push_back( y.create_pi() );
      auto builder = [&]( xag_network& dest, std::vector<sig> const& leaves ) -> sig {
        std::vector<sig> as;
        auto l2 = [&]( std::string const& s ) { sig acc = dest.get_constant( false ); auto t = s; t.erase( std::remove( t.begin(), t.end(), ' ' ), t.end() );
          if ( t == "0" || t.empty() ) return acc; for ( auto const& u : split( t, '+' ) ) { if ( u == "1" ) acc = dest.create_not( acc ); else acc = dest.create_xor( acc, leaves[std::stoul( u.substr( 1 ) ) - 1] ); } return acc; };
        for ( size_t i = 0; i < k; ++i )
        {
          sig a = l2( rec[3 + 2 * i] ), b = l2( rec[4 + 2 * i] );
          for ( int j : sides[i].first ) a = dest.create_xor( a, as[j] );
          for ( int j : sides[i].second ) b = dest.create_xor( b, as[j] );
          as.push_back( dest.create_and( a, b ) );
        }
        sig oo = l2( rec[3 + 2 * k] );
        for ( size_t i = 0; i < k; ++i ) if ( ( omask >> i ) & 1 ) oo = dest.create_xor( oo, as[i] );
        return oo;
      };
      y.create_po( apply_spectral_transformations( y, seq, ypis, builder ) );
      y = cleanup_dangling( y );
      auto ytt = simulate<kitty::dynamic_truth_table>( y, default_simulator<kitty::dynamic_truth_table>( n ) )[0];
      if ( ytt == repr )
      {
        xag_index_list il; encode( il, y );
        auto raw = il.raw();
        out << kitty::to_hex( repr ) << " " << k << " " << order << " ";
        for ( size_t i = 0; i < raw.size(); ++i ) out << ( i ? "," : "" ) << raw[i];
        out << "\n";
        done = true;
      }
    }
    if ( done ) ++ok; else ++bad_tr;
    rec.clear();
    if ( total % 10000 == 0 ) std::fprintf( stderr, "%llu processed, %llu ok\n", (unsigned long long)total, (unsigned long long)ok );
  };
  while ( std::getline( in, line ) )
  {
    if ( line.empty() ) { flush(); continue; }
    rec.push_back( line );
  }
  flush();
  std::fprintf( stderr, "total %llu ok %llu anf_mismatch %llu transform_mismatch %llu step_limited %llu\n",
                (unsigned long long)total, (unsigned long long)ok, (unsigned long long)bad_anf, (unsigned long long)bad_tr,
                (unsigned long long)limited );
  return bad_tr + bad_anf ? 1 : 0;
}
