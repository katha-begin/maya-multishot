#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Vendor NodeGraphQt library into the repository.

This script downloads and installs NodeGraphQt into the vendor/ directory
for version control and offline use.

Usage:
    python vendor_nodegraphqt.py

Author: CTX Pipeline
Date: 2026-02-18
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import shutil
import tempfile
import subprocess


def main():
    """Main function to vendor NodeGraphQt."""
    
    print("\n" + "="*60)
    print("Vendoring NodeGraphQt Library")
    print("="*60 + "\n")
    
    # Get project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    vendor_dir = os.path.join(script_dir, 'vendor')
    nodegraphqt_dir = os.path.join(vendor_dir, 'NodeGraphQt')
    
    # Check if already vendored
    if os.path.exists(nodegraphqt_dir):
        print("NodeGraphQt already exists in vendor/")
        response = input("Do you want to re-download? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
        
        print("Removing existing NodeGraphQt...")
        shutil.rmtree(nodegraphqt_dir)
    
    # Create vendor directory
    if not os.path.exists(vendor_dir):
        os.makedirs(vendor_dir)
        print("Created vendor/ directory")
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    print("Using temp directory: {}".format(temp_dir))
    
    try:
        # Download NodeGraphQt using pip
        print("\nDownloading NodeGraphQt...")
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'download',
            'NodeGraphQt',
            '--no-deps',
            '--dest', temp_dir
        ])
        
        # Find downloaded file
        files = os.listdir(temp_dir)
        nodegraphqt_file = None
        for f in files:
            if f.startswith('NodeGraphQt') or f.startswith('nodegraphqt'):
                nodegraphqt_file = os.path.join(temp_dir, f)
                break
        
        if not nodegraphqt_file:
            print("ERROR: Could not find downloaded NodeGraphQt file")
            return
        
        print("Downloaded: {}".format(os.path.basename(nodegraphqt_file)))
        
        # Extract if it's a wheel or tar.gz
        if nodegraphqt_file.endswith('.whl'):
            # Unzip wheel
            import zipfile
            print("Extracting wheel...")
            with zipfile.ZipFile(nodegraphqt_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Move NodeGraphQt directory
            extracted_dir = os.path.join(temp_dir, 'NodeGraphQt')
            if os.path.exists(extracted_dir):
                shutil.move(extracted_dir, nodegraphqt_dir)
            
        elif nodegraphqt_file.endswith('.tar.gz'):
            # Extract tar.gz
            import tarfile
            print("Extracting tar.gz...")
            with tarfile.open(nodegraphqt_file, 'r:gz') as tar_ref:
                tar_ref.extractall(temp_dir)
            
            # Find extracted directory
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                if os.path.isdir(item_path) and 'NodeGraphQt' in item:
                    # Move NodeGraphQt subdirectory
                    src = os.path.join(item_path, 'NodeGraphQt')
                    if os.path.exists(src):
                        shutil.move(src, nodegraphqt_dir)
                    
                    # Copy LICENSE
                    license_src = os.path.join(item_path, 'LICENSE.md')
                    if os.path.exists(license_src):
                        shutil.copy(license_src, os.path.join(vendor_dir, 'NodeGraphQt_LICENSE.md'))
                    break
        
        # Verify installation
        if os.path.exists(nodegraphqt_dir):
            print("\n" + "="*60)
            print("SUCCESS: NodeGraphQt vendored successfully!")
            print("="*60)
            print("Location: {}".format(nodegraphqt_dir))
            print("\nYou can now use NodeGraphQt without pip install.")
            print("The library is version-controlled in your repo.")
            print("\nTo use:")
            print("  from tests import launch_nodegraphqt")
            print("  launch_nodegraphqt.launch()")
            print("="*60 + "\n")
        else:
            print("\nERROR: NodeGraphQt directory not found after extraction")
            print("Please vendor manually. See: tests/VENDORING_NodeGraphQt.md")
    
    except subprocess.CalledProcessError as e:
        print("\nERROR: Failed to download NodeGraphQt")
        print("Error: {}".format(e))
        print("\nPlease install manually:")
        print("  pip install NodeGraphQt")
        print("\nOr vendor manually. See: tests/VENDORING_NodeGraphQt.md")
    
    except Exception as e:
        print("\nERROR: {}".format(e))
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up temp directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print("\nCleaned up temp directory")


if __name__ == '__main__':
    main()

