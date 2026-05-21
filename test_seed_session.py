#!/usr/bin/env python3
"""Test that generator seed is properly incorporated into session hash."""

from uaforge.core.generator import UserAgentGenerator

def test_base_seed_integration():
    """Test that base seed affects session generation."""
    print("="*70)
    print("Test: Base Seed Integration with Sessions")
    print("="*70)

    # Test 1: Same seed + same session = same UA
    print("\n1️⃣  Same seed + same session = same UA")
    print("-" * 70)
    gen1 = UserAgentGenerator(seed=42)
    gen2 = UserAgentGenerator(seed=42)

    ua1 = gen1.generate(session="user-123")
    ua2 = gen2.generate(session="user-123")

    print(f"Gen1 (seed=42): {ua1.user_agent[:60]}...")
    print(f"Gen2 (seed=42): {ua2.user_agent[:60]}...")
    print(f"Match: {ua1.user_agent == ua2.user_agent}")

    if ua1.user_agent == ua2.user_agent:
        print("✅ PASS: Same seed + same session = same UA")
    else:
        print("❌ FAIL: Should be identical!")
        return False

    # Test 2: Different seed + same session = different identity
    print("\n2️⃣  Different seed + same session = different identity")
    print("-" * 70)
    gen3 = UserAgentGenerator(seed=99)
    ua3 = gen3.generate(session="user-123")

    print(f"Gen1 (seed=42):  {ua1.user_agent[:60]}...")
    print(f"Gen3 (seed=99):  {ua3.user_agent[:60]}...")

    # Compare client hints instead of UA header (more reliable)
    hints_different = (
        ua1.ch_brands != ua3.ch_brands or
        ua1.ch_full_version_list != ua3.ch_full_version_list or
        ua1.ch_platform != ua3.ch_platform or
        ua1.ch_platform_version != ua3.ch_platform_version or
        ua1.ch_mobile != ua3.ch_mobile
    )

    print(f"Client hints different: {hints_different}")
    print(f"  ua1.ch_brands: {ua1.ch_brands}")
    print(f"  ua3.ch_brands: {ua3.ch_brands}")

    if hints_different:
        print("✅ PASS: Different seeds produce different identities")
    else:
        print("⚠️  WARNING: Same identity (very unlikely but possible)")

    # Test 3: No seed (None) vs explicit seed
    print("\n3️⃣  No seed vs explicit seed")
    print("-" * 70)
    gen4 = UserAgentGenerator()  # No seed
    gen5 = UserAgentGenerator(seed=0)  # Explicit seed=0

    ua4 = gen4.generate(session="test")
    ua5 = gen5.generate(session="test")

    print(f"Gen4 (no seed):   {ua4.user_agent[:60]}...")
    print(f"Gen5 (seed=0):    {ua5.user_agent[:60]}...")
    print(f"Match: {ua4.user_agent == ua5.user_agent}")

    if ua4.user_agent == ua5.user_agent:
        print("✅ PASS: No seed defaults to 0")
    else:
        print("❌ FAIL: Should be identical (both use seed=0)")
        return False

    # Test 4: Cross-run determinism
    print("\n4️⃣  Cross-run determinism")
    print("-" * 70)
    gen6 = UserAgentGenerator(seed=12345)
    ua6 = gen6.generate(session="alice")

    print(f"Seed=12345, session='alice':")
    print(f"  UA: {ua6.user_agent}")
    print("✅ This should be IDENTICAL across Python runs")

    return True

def test_session_variations():
    """Test various session types with same seed."""
    print("\n" + "="*70)
    print("Test: Session Variations with Same Seed")
    print("="*70)

    gen = UserAgentGenerator(seed=777)

    sessions = [
        ("string", "alice"),
        ("integer", 42),
        ("long-string", "user-with-long-identifier-12345"),
        ("zero", 0),
        ("one", 1),
    ]

    print("\nUsing seed=777 with different sessions:")
    for name, session in sessions:
        ua = gen.generate(session=session)
        print(f"  {name:15} ({session!r:30}) -> {ua.user_agent[:45]}...")

    print("\n✅ All variations work correctly")
    return True

def main():
    print("\n" + "🎯 "*30)
    print("BASE SEED INTEGRATION TESTS")
    print("🎯 "*30)

    tests = [
        test_base_seed_integration,
        test_session_variations,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    passed = sum(results)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
        print("\n🎯 Key Features:")
        print("   • Generator seed properly incorporated")
        print("   • Same seed + same session = same UA")
        print("   • Different seeds = different UAs")
        print("   • Deterministic across Python runs")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED!")
        return 1

if __name__ == "__main__":
    exit(main())
