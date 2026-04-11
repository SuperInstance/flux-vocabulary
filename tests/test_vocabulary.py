"""Basic tests for flux-vocabulary."""
import sys
sys.path.insert(0, "src")

from flux_vocabulary import Vocabulary, VocabEntry

def test_create_vocab():
    v = Vocabulary("test")
    assert v.name == "test"

def test_add_entry():
    v = Vocabulary("test")
    entry = VocabEntry(
        pattern="add $a and $b",
        bytecode_template="MOVI R0, ${a}\nMOVI R1, ${b}\nADD R0, R0, R1\nHALT",
        result_reg=0,
        name="addition",
        description="Add two numbers",
        tags=["math"]
    )
    v.add(entry)
    assert len(v.entries) == 1

if __name__ == "__main__":
    test_create_vocab()
    test_add_entry()
    print("All tests passed!")
