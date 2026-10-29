// qbank driver around mockturtle (MIT): AIGER -> XAG -> MC-oriented cut rewriting
// (cut_rewriting_with_compatibility_graph + mc_cost) with a resynthesis functor that is mockturtle's
// future::xag_minmc_resynthesis (xag_minmc2.hpp) with one change: the exact spectral canonization of a cut function
// is bounded by a step limit (hybrid_limit.hpp); a cut whose canonization reaches the limit is left unchanged.
// Databases: mockturtle's embedded optimum-MC XAGs for <= 5 inputs, and optionally a 6-input database file built
// from NIST's circuits by build_db6.cpp with the same step limit.
// -> print the resulting XAG in a line format read by qbank (src/qbank/core/xag.py: from_minmc_text).
#include <csignal>
#include <cstdio>
#include <iostream>
#include <unistd.h>
#include <string>
#include <lorina/aiger.hpp>
#include <mockturtle/networks/xag.hpp>
#include <mockturtle/io/aiger_reader.hpp>
#include <mockturtle/algorithms/cut_rewriting.hpp>
#include <mockturtle/algorithms/cleanup.hpp>
#include <mockturtle/algorithms/simulation.hpp>
#include <mockturtle/utils/cost_functions.hpp>
#include <mockturtle/utils/index_list/index_list.hpp>
#include <mockturtle/algorithms/equivalence_classes.hpp>
#include <mockturtle/algorithms/detail/minmc_xags.hpp>
#include <lorina/detail/utils.hpp>
#include <fstream>
#include <unordered_map>
#include "hybrid_limit.hpp"

using namespace mockturtle;

// canonization step limit for cut functions during rewriting (argv[6]; default below). The database was built with
// 10^8 steps; a lower limit here only skips more cuts, it never changes a representative that is found.
static unsigned CANON_STEP_LIMIT = 10000u;

// copy of future::xag_minmc_resynthesis (mockturtle d9e0249, MIT) with the bounded canonization
class minmc_resynthesis_limited
{
public:
  minmc_resynthesis_limited()
  {
    for ( auto i = 0u; i < detail::minmc_xags.size(); ++i )
      for ( auto const& [_, word, repr, expr] : detail::minmc_xags[i] )
        db_[i][word] = repr;
  }

  void load_from_file( std::string const& filename )
  {
    kitty::dynamic_truth_table func( 6u );
    std::ifstream in( filename, std::ifstream::in );
    std::string line;
    while ( std::getline( in, line ) )
    {
      const auto vline = lorina::detail::split( line, " " );
      kitty::create_from_hex_string( func, vline[0] );
      const auto sindexes = lorina::detail::split( vline[3], "," );
      std::vector<uint32_t> index_list( sindexes.size() );
      std::transform( sindexes.begin(), sindexes.end(), index_list.begin(), [&]( std::string const& s ) { return static_cast<uint32_t>( std::stoul( s ) ); } );
      db_[6u][*func.cbegin()] = index_list;
    }
  }

  size_t db_entries( uint32_t k ) const { return db_[k].size(); }
  uint64_t limit_hits{ 0 }, misses{ 0 };

  template<typename LeavesIterator, typename Fn>
  void operator()( xag_network& ntk, kitty::dynamic_truth_table const& function, LeavesIterator begin, LeavesIterator end, Fn&& fn )
  {
    const auto num_vars = function.num_vars();
    uint64_t repr;
    std::vector<kitty::detail::spectral_operation> trans;
    if ( const auto it = cache_[num_vars].find( *function.cbegin() ); it != cache_[num_vars].end() )
    {
      if ( !it->second.ok ) return;
      repr = it->second.repr;
      trans = it->second.trans;
    }
    else
    {
      const auto [r, exact] = hybrid_canon_limit( function, CANON_STEP_LIMIT, [&]( auto const& ops ) { trans = ops; } );
      cache_[num_vars][*function.cbegin()] = { exact, exact ? *r.cbegin() : 0u, trans };
      if ( !exact ) { ++limit_hits; return; }
      repr = *r.cbegin();
    }
    const auto it = db_[num_vars].find( repr );
    if ( it == db_[num_vars].end() ) { ++misses; return; }
    const auto f = apply_spectral_transformations( ntk, trans, std::vector<xag_network::signal>( begin, end ), [&]( xag_network& ntk, std::vector<xag_network::signal> const& leaves ) {
      xag_index_list il{ it->second };
      std::vector<xag_network::signal> pos;
      insert( ntk, std::begin( leaves ), std::begin( leaves ) + il.num_pis(), il, [&]( xag_network::signal const& f ) { pos.push_back( f ); } );
      return pos[0u];
    } );
    fn( f );
  }

private:
  struct entry { bool ok; uint64_t repr; std::vector<kitty::detail::spectral_operation> trans; };
  std::vector<std::unordered_map<uint64_t, std::vector<uint32_t>>> db_{ 7u };
  std::vector<std::unordered_map<uint64_t, entry>> cache_{ 7u };
};

static uint32_t count_ands( xag_network const& x )
{
  uint32_t n = 0;
  x.foreach_gate( [&]( auto const& g ) { if ( x.is_and( g ) ) ++n; } );
  return n;
}

// a failed assertion or a crash must end the process with an exit code, not a signal: a process killed by a signal
// makes macOS show a crash-report dialog
static void on_fatal( int sig )
{
  const char msg[] = "minmc: fatal signal\n";
  (void)!write( 2, msg, sizeof( msg ) - 1 );
  _exit( 70 + ( sig & 15 ) );
}

int main( int argc, char** argv )
{
  for ( int sig : { SIGABRT, SIGSEGV, SIGBUS, SIGFPE, SIGILL } ) std::signal( sig, on_fatal );
  if ( argc < 3 ) { std::fprintf( stderr, "usage: minmc in.aig cut_size [db6.txt|-] [rounds] [cut_limit] [canon_step_limit]\n" ); return 2; }
  try {
  xag_network xag;
  if ( lorina::read_aiger( argv[1], aiger_reader( xag ) ) != lorina::return_code::success ) { std::fprintf( stderr, "read error\n" ); return 1; }
  uint32_t cut_size = std::stoul( argv[2] );
  minmc_resynthesis_limited resyn;
  if ( argc > 3 && std::string( argv[3] ) != "-" ) resyn.load_from_file( argv[3] );
  if ( cut_size == 6 && resyn.db_entries( 6 ) == 0 ) { std::fprintf( stderr, "cut size 6 needs the 6-input database\n" ); return 2; }
  uint32_t rounds = argc > 4 ? std::stoul( argv[4] ) : 5;
  // network_cuts::max_cut_num = 26 in this mockturtle commit; cut_limit must stay below it (mockturtle default 25)
  uint32_t cut_limit = argc > 5 ? std::stoul( argv[5] ) : 25;
  if ( argc > 6 ) CANON_STEP_LIMIT = std::stoul( argv[6] );
  if ( cut_size < 2 || cut_size > 6 || cut_limit < 1 || cut_limit > 25 ) { std::fprintf( stderr, "bad cut_size/cut_limit\n" ); return 2; }
  std::fprintf( stderr, "ands_before %u\n", count_ands( xag ) );
  for ( uint32_t r = 0; r < rounds; ++r )
  {
    uint32_t before = count_ands( xag );
    cut_rewriting_params ps;
    ps.cut_enumeration_ps.cut_size = cut_size;
    ps.cut_enumeration_ps.cut_limit = cut_limit;
    cut_rewriting_with_compatibility_graph( xag, resyn, ps, nullptr, mc_cost<xag_network>() );
    xag = cleanup_dangling( xag );
    if ( count_ands( xag ) >= before ) break;
  }
  const uint32_t ands_rewritten = count_ands( xag );
  // networks with <= 6 inputs: also resynthesize every output as a whole from its truth table with the same databases
  // (the root cut containing all inputs is often not among the enumerated cuts); keep whichever has fewer ANDs
  uint32_t ands_collapsed = 0;
  if ( xag.num_pis() <= 6 )
  {
    CANON_STEP_LIMIT = 100000000u;                     // whole functions: the limit of the database build
    const auto tts = simulate<kitty::dynamic_truth_table>( xag, default_simulator<kitty::dynamic_truth_table>( xag.num_pis() ) );
    xag_network y;
    std::vector<xag_network::signal> pis;
    for ( auto i = 0u; i < xag.num_pis(); ++i ) pis.push_back( y.create_pi() );
    bool ok = true;
    for ( auto const& tt : tts )
    {
      bool got = false;
      resyn( y, tt, pis.begin(), pis.end(), [&]( auto const& f ) { y.create_po( f ); got = true; } );
      if ( !got ) { ok = false; break; }
    }
    if ( ok )
    {
      y = cleanup_dangling( y );
      ands_collapsed = count_ands( y );
      if ( ands_collapsed < ands_rewritten ) xag = y;
    }
  }
  std::fprintf( stderr, "ands_rewritten %u\nands_collapsed %u\n", ands_rewritten, ands_collapsed );
  std::fprintf( stderr, "ands_after %u\ncanon_limit_hits %llu\ndb_misses %llu\n", count_ands( xag ),
                (unsigned long long)resyn.limit_hits, (unsigned long long)resyn.misses );
  // text format: "pis n", then gates "g id and|xor a b" (signal = 2*node + complement), then "po sig"
  std::printf( "pis %u\n", xag.num_pis() );
  xag.foreach_gate( [&]( auto const& n ) {
    std::vector<uint32_t> f;
    xag.foreach_fanin( n, [&]( auto const& s ) { f.push_back( 2 * xag.node_to_index( xag.get_node( s ) ) + ( xag.is_complemented( s ) ? 1 : 0 ) ); } );
    std::printf( "g %u %s %u %u\n", xag.node_to_index( n ), xag.is_and( n ) ? "and" : "xor", f[0], f[1] );
  } );
  xag.foreach_po( [&]( auto const& s ) {
    std::printf( "po %u\n", 2 * xag.node_to_index( xag.get_node( s ) ) + ( xag.is_complemented( s ) ? 1 : 0 ) );
  } );
  return 0;
  } catch ( std::exception const& e ) { std::fprintf( stderr, "minmc: %s\n", e.what() ); return 3; }
}
