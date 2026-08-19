<?php
    $to = "info@example.com";
    $subject = $_POST['Contact Us - Oxentech Design Agency'];

    $message = "
    <html>
    <body>
    <table>

    <tr>
    <td>Name</td>
    <td>".$_POST['name']."</td>
    </tr>
    <tr>
    <td>Subject</td>
    <td>".$_POST['subject']."</td>
    </tr>
    <tr>
    <td>Phone</td>
    <td>".$_POST['phone']."</td>
    </tr>
    <tr>
    <td>Email</td>
    <td>".$_POST['email']."</td>
    </tr>  
    <td>Message</td>
    <td>".$_POST['message']."</td>
    </tr>



    </table>
    </body>
    </html>
    ";

    // Always set content-type when sending HTML email
    $headers = "MIME-Version: 1.0" . "\r\n";
    $headers .= "Content-type:text/html;charset=UTF-8" . "\r\n";

    // More headers
    $headers .= 'From: <support@example.com>' . "\r\n";

    mail($to,$subject,$message,$headers);

    header('location: thankyou.html');

?>