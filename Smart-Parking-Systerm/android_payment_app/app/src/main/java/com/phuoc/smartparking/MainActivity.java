package com.phuoc.smartparking;

import android.os.Bundle;
import android.view.View;
import android.widget.ImageView;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import com.bumptech.glide.Glide;
import com.google.firebase.database.DataSnapshot;
import com.google.firebase.database.DatabaseError;
import com.google.firebase.database.DatabaseReference;
import com.google.firebase.database.FirebaseDatabase;
import com.google.firebase.database.ValueEventListener;

public class MainActivity extends AppCompatActivity {

    // Thông tin ngân hàng
    String BANK_ID = "MB";
    String ACCOUNT_NO = "0382597918";
    String ACCOUNT_NAME = "TRINH DUY PHUOC";

    TextView txtPlate, txtAmount, txtStatusHint;
    ImageView imgQR;
    DatabaseReference dbRef;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        txtPlate = findViewById(R.id.txtPlate);
        txtAmount = findViewById(R.id.txtAmount);
        txtStatusHint = findViewById(R.id.txtStatusHint);
        imgQR = findViewById(R.id.imgQR);

        // Trỏ đúng vào link Singapore của bạn
        dbRef = FirebaseDatabase.getInstance("https://smartparkingsystem-1e749-default-rtdb.asia-southeast1.firebasedatabase.app/").getReference("ParkingSystem");

        dbRef.child("CurrentVehicle").addValueEventListener(new ValueEventListener() {
            @Override
            public void onDataChange(DataSnapshot snapshot) {
                if (!snapshot.exists()) return;

                Integer status = snapshot.child("status").getValue(Integer.class);
                String plate = snapshot.child("license_plate").getValue(String.class);
                Long amount = snapshot.child("amount").getValue(Long.class);

                if (status != null && status == 2) {
                    // TRẠNG THÁI CHỜ TIỀN: Hiện QR
                    txtPlate.setText(plate);
                    txtAmount.setText(String.format("%,d VNĐ", amount));
                    txtStatusHint.setText("Vui lòng quét mã để thanh toán");
                    txtStatusHint.setTextColor(0xFF757575);

                    String description = "Thanh toan xe " + plate;
                    String qrUrl = "https://api.vietqr.io/image/" + BANK_ID + "-" + ACCOUNT_NO + "-compact.jpg" +
                            "?amount=" + amount + "&addInfo=" + description + "&accountName=" + ACCOUNT_NAME;

                    Glide.with(MainActivity.this).load(qrUrl).into(imgQR);
                }
                else if (status != null && status == 3) {
                    // TRẠNG THÁI ĐÃ NHẬN TIỀN: Báo thành công
                    txtPlate.setText("THANH TOÁN THÀNH CÔNG");
                    txtAmount.setText("MỜI XE RA KHỎI BÃI");
                    txtStatusHint.setText("Hệ thống đang mở Barie...");
                    txtStatusHint.setTextColor(0xFF4CAF50); // Màu xanh lá

                    // Hiện icon thành công thay cho QR
                    imgQR.setImageResource(android.R.drawable.checkbox_on_background);
                }
                else {
                    // TRẠNG THÁI NGHỈ
                    txtPlate.setText("XIN CHÀO!");
                    txtAmount.setText("Hệ thống sẵn sàng");
                    txtStatusHint.setText("Đang chờ xe tới...");
                    imgQR.setImageDrawable(null);
                }
            }

            @Override
            public void onCancelled(DatabaseError error) {}
        });
    }
}