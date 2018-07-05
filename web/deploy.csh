#! /bin/tcsh

foreach f ( histogram.css histogram.js index.html )

  aws s3 cp $f s3://tinker-access/${f}

end
