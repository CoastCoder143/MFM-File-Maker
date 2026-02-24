# Research: MIKEIO and .mfm File Production

## What is MIKEIO?

**MIKEIO** is a Python library developed by DHI for reading, writing, and manipulating MIKE files. It's the official Python interface for working with various MIKE file formats used by DHI's modeling software suite (MIKE by DHI).

### Key Features

- **File Format Support**: Read and write dfs0, dfs1, dfs2, dfs3, dfsu, and mesh files
- **PFS File Support**: Read and write PFS (Parameter File System) files, which includes .mfm files
- **Cross-Platform**: Works on Windows and Linux
- **Python Support**: Compatible with Python 3.10 - 3.13
- **Well-Tested**: 95% test coverage with extensive test suite

### Installation

```bash
pip install mikeio
```

**Important**: Don't use conda - the conda version is outdated.

### Documentation

- Official Documentation: https://dhi.github.io/mikeio/
- GitHub Repository: https://github.com/DHI/mikeio
- Getting Started Guide: https://dhi.github.io/getting-started-with-mikeio/intro.html

## Understanding .mfm Files

### What are .mfm Files?

.mfm files are **MIKE FM (Flexible Mesh) setup files** used to configure MIKE 21/3 FM models. They are actually **PFS (Parameter File System) files** with a .mfm extension.

### File Structure

.mfm files have a hierarchical, section-based structure:

```
[SECTION_NAME]
   parameter_name = value
   file_name = |path/to/file.dfs0|
   
   [NESTED_SECTION]
      nested_param = value
   EndSect  // NESTED_SECTION
   
EndSect  // SECTION_NAME
```

Key characteristics:
- Sections are defined with `[SECTION_NAME]` and closed with `EndSect`
- Parameters can be strings, numbers, lists, or file paths
- File paths are enclosed in pipe characters: `|filename.dfs0|`
- Comments start with `//`
- Sections can be nested
- Default encoding is cp1252 (Windows)

## Working with .mfm Files Using MIKEIO

### Reading .mfm Files

Since .mfm files are PFS files, you use mikeio's PFS module:

```python
import mikeio

# Read an .mfm file
mfm = mikeio.PfsDocument('model_setup.mfm')

# Access sections and parameters
print(mfm.targets)  # List all top-level sections
print(mfm.DREDGER_1.file_name)  # Access nested parameters
```

### Modifying .mfm Files

```python
import mikeio

# Read the .mfm file
mfm = mikeio.PfsDocument('model_setup.mfm')

# Modify parameters
mfm.DREDGER_1.file_name = '|new_input.dfs0|'
mfm.MORPHOLOGY.OUTPUTS.OUTPUT_1.file_name = '|new_output.dfsu|'

# Add new sections
mfm['NEW_SECTION'] = mikeio.PfsSection({
    'parameter1': 100,
    'parameter2': [1.0, 2.0, 3.0]
})

# Write back to file
mfm.write('modified_setup.mfm')
```

### Creating .mfm Files from Scratch

```python
import mikeio

# Create a structure dictionary
structure = {
    'FemEngineHD': {
        'DREDGER_1': {
            'file_name': '|input.dfs0|',
            'type': 1,
            'enabled': True
        },
        'MORPHOLOGY': {
            'enabled': True,
            'OUTPUTS': {
                'OUTPUT_1': {
                    'file_name': '|output.dfsu|',
                    'type': 'dfsu'
                }
            }
        }
    }
}

# Create PfsDocument
mfm = mikeio.PfsDocument(structure)

# Write to file
mfm.write('new_model.mfm')
```

### Key PFS/MFM Operations

#### 1. Find and Replace Values

```python
# Replace all occurrences of a value throughout the document
mfm.find_replace(old_value, new_value)
```

#### 2. Access Nested Sections

```python
# Direct attribute access
value = mfm.MORPHOLOGY.OUTPUTS.OUTPUT_1.file_name

# Dictionary-style access
value = mfm['MORPHOLOGY']['OUTPUTS']['OUTPUT_1']['file_name']
```

#### 3. Check Section Existence

```python
if 'DREDGER_1' in mfm:
    print("DREDGER_1 section exists")
```

#### 4. Iterate Over Sections

```python
for key, section in mfm.items():
    print(f"Section: {key}")
    if isinstance(section, mikeio.PfsSection):
        for param, value in section.items():
            print(f"  {param} = {value}")
```

#### 5. Copy and Modify

```python
# Create a copy to avoid modifying the original
mfm_copy = mfm.copy()
mfm_copy.DREDGER_1.file_name = '|different_input.dfs0|'
```

## Comparison: Current Script vs MIKEIO

### Current Approach (edit_mfm.py)

**Pros:**
- Lightweight - no external dependencies
- Fast for simple operations
- Direct text manipulation with regex
- Works immediately without MIKEIO installation

**Cons:**
- Limited to text-based pattern matching
- Must manually handle file structure
- Fragile to format variations
- No validation of .mfm structure

### MIKEIO Approach

**Pros:**
- Understands PFS/MFM structure natively
- Type-safe parameter access
- Can validate structure
- Easy to navigate complex nested sections
- Official DHI library with ongoing support
- Can work with other MIKE files (dfs0, dfsu, etc.)

**Cons:**
- Requires MIKEIO installation
- Larger dependency (though minimal)
- Slightly more complex API for simple operations

## Recommendations

### When to Use Current Script

Use `edit_mfm.py` when:
- You need a lightweight solution
- You only need to update specific known paths
- Users may not have Python packages installed
- The .mfm structure is simple and consistent

### When to Use MIKEIO

Consider migrating to MIKEIO when:
- You need to read/write other MIKE files (dfs0, dfsu)
- The .mfm structure is complex or varies
- You want structural validation
- You're building a larger MIKE workflow automation
- You need to manipulate complex nested sections

### Hybrid Approach

A practical solution might be to:
1. Keep the current lightweight script for quick path updates
2. Add optional MIKEIO support for advanced operations
3. Document both approaches for users

Example:

```python
# Try using MIKEIO if available, fall back to regex approach
try:
    import mikeio
    USE_MIKEIO = True
except ImportError:
    USE_MIKEIO = False
    print("MIKEIO not found, using text-based approach")

if USE_MIKEIO:
    # Use structured PFS manipulation
    mfm = mikeio.PfsDocument(template_path)
    mfm.DREDGER_1.file_name = f'|{dfs0_path}|'
    mfm.write(output_path)
else:
    # Use current regex-based approach
    # ... (current implementation)
```

## Example: Batch Processing with MIKEIO

Here's how the current script's batch processing could be implemented with MIKEIO:

```python
import mikeio
from pathlib import Path

def process_with_mikeio(template_path, dfs0_folder, output_dfsu_folder):
    """Process multiple .dfs0 files using MIKEIO."""
    
    # Read template once
    template = mikeio.PfsDocument(template_path)
    template_name = Path(template_path).stem
    
    # Get all .dfs0 files
    dfs0_files = sorted(Path(dfs0_folder).glob('*.dfs0'))
    
    print(f"Processing {len(dfs0_files)} files with template: {template_name}")
    
    success_count = 0
    failed_files = []
    
    for dfs0_file in dfs0_files:
        try:
            # Create a copy for this file
            mfm = template.copy()
            
            # Update DREDGER_1 file_name
            if hasattr(mfm, 'DREDGER_1'):
                mfm.DREDGER_1.file_name = f'|{dfs0_file}|'
            
            # Update MORPHOLOGY OUTPUT_1 file_name
            output_name = f"{template_name}_{dfs0_file.stem}.dfsu"
            output_path = Path(output_dfsu_folder) / output_name
            
            if hasattr(mfm, 'MORPHOLOGY'):
                morphology = mfm.MORPHOLOGY
                if hasattr(morphology, 'OUTPUTS'):
                    outputs = morphology.OUTPUTS
                    if hasattr(outputs, 'OUTPUT_1'):
                        outputs.OUTPUT_1.file_name = f'|{output_path}|'
            
            # Write output
            output_mfm = Path('output') / f"{template_name}_{dfs0_file.stem}.mfm"
            mfm.write(output_mfm)
            
            print(f"✓ {dfs0_file.name} -> {output_mfm.name}")
            success_count += 1
            
        except Exception as e:
            print(f"✗ {dfs0_file.name}: {e}")
            failed_files.append((dfs0_file.name, str(e)))
    
    # Summary
    print(f"\nCompleted: {success_count}/{len(dfs0_files)} successful")
    if failed_files:
        print("\nFailed files:")
        for filename, error in failed_files:
            print(f"  - {filename}: {error}")

# Usage
process_with_mikeio(
    'input-mfm/template.mfm',
    'input_dfs0_folder',
    'output_dfsu_folder'
)
```

## Additional MIKEIO Capabilities

Beyond .mfm files, MIKEIO can:

1. **Read/Write DFS Files** (time series and spatial data):
   ```python
   # Read .dfs0 (time series)
   ds = mikeio.open('timeseries.dfs0')
   df = ds.to_dataframe()
   
   # Read .dfsu (unstructured mesh results)
   dfsu = mikeio.open('results.dfsu')
   data = dfsu.read()
   ```

2. **Mesh Operations**:
   ```python
   # Work with flexible mesh geometries
   mesh = dfsu.geometry
   print(f"Elements: {mesh.n_elements}")
   print(f"Nodes: {mesh.n_nodes}")
   ```

3. **Data Manipulation**:
   ```python
   # Extract, filter, interpolate data
   subset = data.sel(time=slice('2020-01-01', '2020-12-31'))
   point_data = dfsu.extract(x=12.5, y=55.5)
   ```

## Conclusion

MIKEIO is a powerful library for working with MIKE files, including .mfm files (which are PFS files). While the current `edit_mfm.py` script provides a lightweight solution for specific path updates, MIKEIO offers:

- Structural understanding of .mfm files
- Robust handling of complex configurations
- Integration with the broader MIKE ecosystem
- Official DHI support and ongoing development

For users working extensively with MIKE models, learning MIKEIO is valuable. For simple .mfm path updates, the current script remains practical and efficient.

## References

- MIKEIO GitHub: https://github.com/DHI/mikeio
- MIKEIO Documentation: https://dhi.github.io/mikeio/
- Getting Started with MIKEIO: https://dhi.github.io/getting-started-with-mikeio/
- DHI Technologies: https://www.dhigroup.com/technologies/mikepoweredbydhi
- PyPI Package: https://pypi.org/project/mikeio/
