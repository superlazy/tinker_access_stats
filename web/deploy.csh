#! /bin/tcsh

foreach f ( histogram.css histogram.js index.html )

  aws --profile personal s3 cp $f s3://tinker-access/${f}

end
