"""Test complete demo pipeline end-to-end."""
import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.mock_pipeline import mock_pipeline
from services.demo_simulator import demo_simulator


async def test_full_pipeline():
    """Test complete pipeline with progress tracking."""
    
    print("=" * 60)
    print("TESTING MOCK PIPELINE")
    print("=" * 60)
    
    # Track progress updates
    progress_updates = []
    
    async def progress_callback(job_id, progress, stage):
        progress_updates.append({"progress": progress, "stage": stage})
        print(f"  [{progress}%] {stage}")
    
    try:
        # Run pipeline
        print("\n1. Starting pipeline simulation...")
        result = await mock_pipeline.process_job(
            job_id="test_job_123",
            video_id="demo_real_video_001",
            target_languages=["es"],
            user_id="demo_user",
            progress_callback=progress_callback
        )
        
        # Verify results
        print("\n2. Verifying results...")
        assert "es" in result, "Spanish result not found"
        assert result["es"]["dubbed_video_url"], "Dubbed video URL missing"
        assert result["es"]["dubbed_video_url"].endswith("es.mov"), "Incorrect dubbed video URL"
        assert len(progress_updates) >= 5, f"Expected at least 5 progress updates, got {len(progress_updates)}"
        assert progress_updates[-1]["progress"] == 100, "Final progress should be 100%"
        
        print("\n" + "=" * 60)
        print("✓ PIPELINE TEST PASSED")
        print("=" * 60)
        print(f"  Total stages: {len(progress_updates)}")
        print(f"  Final video: {result['es']['dubbed_video_url']}")
        print(f"  Dubbed audio: {result['es']['dubbed_audio_url']}")
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ ASSERTION FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_demo_simulator():
    """Test demo simulator functions."""
    print("\n" + "=" * 60)
    print("TESTING DEMO SIMULATOR")
    print("=" * 60)
    
    try:
        # Test is_demo_user check
        is_demo = demo_simulator.is_demo_user(email="demo@olleey.com")
        assert is_demo, "Demo user check failed"
        
        is_not_demo = demo_simulator.is_demo_user(email="other@example.com")
        assert not is_not_demo, "Non-demo user should return False"
        
        print("✓ Demo user detection works correctly")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("DEMO PIPELINE TEST SUITE")
    print("=" * 60)
    
    results = []
    
    # Test 1: Demo simulator
    results.append(await test_demo_simulator())
    
    # Test 2: Full pipeline
    results.append(await test_full_pipeline())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ ALL TESTS PASSED")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
