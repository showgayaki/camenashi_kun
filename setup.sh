#!/bin/bash

# 仮想環境に入る
cd `dirname $0`
source .venv/bin/activate

# Pythonバージョン取得
python_ver=(`python -V`)
ver=(${python_ver[1]//./ })
PYTHON_VERSION=${ver[0]}.${ver[1]}

ROOT_DIR=`pwd`
INSTALL_DIR=$ROOT_DIR/.venv/lib/python$PYTHON_VERSION/site-packages/

echo python version: $PYTHON_VERSION
echo root_dir: $ROOT_DIR
echo install_dir: $INSTALL_DIR

export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig

# 必要なパッケージインストール
sudo apt-get install -y unzip gcc g++ make cmake nasm pkg-config python$PYTHON_VERSION-dev libpython$PYTHON_VERSION-dev \
    libgtk2.0-dev libavcodec-dev libavformat-dev libswscale-dev \
    libgstreamer-plugins-base1.0-dev libgstreamer1.0-dev \
    libpng-dev libjpeg-dev libopenexr-dev libtiff-dev libwebp-dev

# ---------
# openh264
# ---------
OPEN_H264='openh264'
git clone https://github.com/cisco/openh264.git
cd $OPEN_H264
make -j4
sudo make install

OPEN_H264_FILE='libopenh264-2.4.1-linux64.7.so'
OPEN_H264_URL='http://ciscobinary.openh264.org/'$OPEN_H264_FILE.bz2
wget $OPEN_H264_URL

bunzip2 $OPEN_H264_FILE.bz2
sudo mv $OPEN_H264_FILE /usr/local/lib/libopenh264.so.2.4.1
chmod 755 /usr/local/lib/libopenh264.so.2.4.1
rm -f $OPEN_H264_FILE.bz2

export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig
ls ${PKG_CONFIG_PATH}

# ---------
# ffmpeg
# ---------
FFMPEG_VER='n6.1.1'
FFMPEG='ffmpeg-'$FFMPEG_VER

export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig
cd $ROOT_DIR
git clone -b $FFMPEG_VER https://github.com/FFmpeg/FFmpeg.git $FFMPEG
cd $FFMPEG
./configure \
    --enable-libopenh264 \
    --enable-optimizations \
    --enable-static \
    --enable-version3 \
    --enable-shared \
    --disable-gpl \
    --disable-doc \
    --disable-htmlpages \
    --disable-manpages \
    --disable-podpages \
    --disable-txtpages \
    --disable-avdevice \
    --disable-postproc \
    --disable-bzlib \
    --disable-iconv \
    --disable-cuda \
    --disable-cuvid \
    --disable-debug \
    --extra-ldflags="-static-libgcc -static-libstdc++"
make -j4
sudo make install
sudo ldconfig
ffmpeg -version

# ---------
# opencv
# ---------
OPENCV_VER='4.9.0'
OPENCV='opencv-'$OPENCV_VER
OPENCV_ZIP=$OPENCV.zip

cd $ROOT_DIR
wget https://github.com/opencv/opencv/archive/$OPENCV_VER.zip -O $OPENCV_ZIP
unzip $OPENCV_ZIP
cd $OPENCV
mkdir build
cd build
cmake \
    -DCMAKE_PREFIX=FFMPEG \
    -DCMAKE_BUILD_TYPE=RELEASE \
    -DCMAKE_INSTALL_PREFIX=$INSTALL_DIR/opencv-python.build \
    -DOPENCV_PYTHON_INSTALL_PATH=$INSTALL_DIR \
    -DHAVE_opencv_python2=OFF \
    -DHAVE_opencv_python3=ON \
    -DBUILD_opencv_python2=OFF \
    -DBUILD_opencv_python3=ON \
    -DPYTHON3_EXECUTABLE=$(which python) \
    -DPYTHON_DEFAULT_EXECUTABLE=$(which python) \
    -DPYTHON3_INCLUDE_DIR=$(python -c "from distutils.sysconfig import get_python_inc; print(get_python_inc())") \
    -DPYTHON3_PACKAGES_PATH=$(python -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())") \
    -DOPENCV_FFMPEG_USE_FIND_PACKAGE=ON \
    -DBUILD_DOCS=OFF \
    -DBUILD_TESTS=OFF \
    -DBUILD_EXAMPLES=OFF \
    -DBUILD_JAVA=OFF \
    -DWITH_1394=OFF \
    -DWITH_CUDA=OFF \
    -DWITH_CUFFT=OFF \
    -DWITH_FFMPEG=ON \
    -DWITH_GSTREAMERE=OFF \
    -DWITH_GTK=ON \
    -DWITH_IPP=OFF \
    -DWITH_JASPERE=OFF \
    -DWITH_JPEG=ON \
    -DWITH_OPENEXR=OFF \
    -DWITH_PNG=ON \
    -DWITH_TIFF=ON \
    -DWITH_V4L=OFF \
    -DWITH_GPHOTO2=OFF \
    -DWITH_CUBLAS=OFF \
    -DWITH_VTK=OFF \
    -DWITH_NVCUVID=OFF \
    ..

make -j4
make install

# # お掃除
cd $ROOT_DIR
rm -rf $OPEN_H264
rm -rf $FFMPEG
rm -rf $OPENCV
rm -rf $OPENCV_ZIP

pip install -r requirements.txt
